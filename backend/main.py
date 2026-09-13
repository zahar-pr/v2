import asyncio
import os
import uuid
from contextlib import asynccontextmanager

import catalog
import db
import domain
import index
import payload
from fastapi import Body, Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sources import SOURCES, active

FRONTEND_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "dist"
)
COOKIE = "provizia_user"
COOKIE_AGE = 60 * 60 * 24 * 365
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "")
PER_PAGE = 12
MAX_PER_PAGE = 60
_workers: list[asyncio.Task] = []


@asynccontextmanager
async def lifespan(_app: FastAPI):
    db.connect()
    if os.environ.get("PROVIZIA_WORKERS", "1") == "1":
        _workers.append(asyncio.create_task(index.prewarm()))
        _workers.append(asyncio.create_task(index.enrich_forever()))
    yield
    for task in _workers:
        task.cancel()


app = FastAPI(title="Провизия — поиск поставщиков продуктов питания", lifespan=lifespan)
app.add_middleware(GZipMiddleware, minimum_size=800)


class WebFiles(StaticFiles):
    def file_response(self, full_path, *args, **kwargs):
        response = super().file_response(full_path, *args, **kwargs)
        path = str(full_path)
        if path.endswith(".html"):
            response.headers["Cache-Control"] = "no-store"
        elif "/assets/" in path:
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        else:
            response.headers["Cache-Control"] = "public, max-age=604800"
        return response


class NoteIn(BaseModel):
    supplierId: str
    text: str = ""


class CompareIn(BaseModel):
    ids: list[str] = []


def user_id(request: Request, response: Response) -> str:
    found = request.cookies.get(COOKIE)
    if not found:
        found = uuid.uuid4().hex
        response.set_cookie(COOKIE, found, max_age=COOKIE_AGE, httponly=True, samesite="lax")
    return found


def _sources_meta() -> list[dict]:
    ready = {source.id for source in active()}
    listed = [
        {"id": source.id, "title": source.title, "active": source.id in ready}
        for source in SOURCES
    ]
    listed.append({"id": "website", "title": "Сайты поставщиков", "active": True})
    listed.append({"id": "wikidata", "title": "Wikidata", "active": True})
    return listed


@app.get("/api/meta")
def api_meta():
    return payload.meta(db.stats(), index.state, _sources_meta())


@app.get("/api/status")
def api_status():
    return {"stats": db.stats(), "status": payload.status(index.state)}


@app.get("/api/suppliers")
async def api_suppliers(
    request: Request,
    response: Response,
    q: str = Query("", max_length=120),
    category: str = Query(catalog.ANY),
    region: str = Query(catalog.ANY_REGION_TITLE),
    city: str = Query(catalog.ANY_CITY_TITLE),
    onlyDocs: bool = Query(False),
    onlyVerified: bool = Query(False),
    onlyWholesale: bool = Query(False),
    sort: str = Query(catalog.SORTS[0]),
    page: int = Query(1, ge=1, le=200),
    perPage: int = Query(PER_PAGE, ge=1, le=MAX_PER_PAGE),
):
    owner = user_id(request, response)
    chosen_category = "" if category in ("", catalog.ANY) else category
    if chosen_category and catalog.category(chosen_category) is None:
        raise HTTPException(400, f"Неизвестная категория «{category}»")

    chosen_region = "" if region in ("", catalog.ANY, catalog.ANY_REGION_TITLE) else region
    chosen_city = "" if city in ("", catalog.ANY, catalog.ANY_CITY_TITLE) else city

    if chosen_city:
        if catalog.city(chosen_city) is None:
            raise HTTPException(404, f"Не знаю город «{chosen_city}»")
        try:
            await index.ensure_city(chosen_city)
        except domain.PlaceNotFound:
            raise HTTPException(404, f"Не нашёл город «{chosen_city}»")
        except domain.SourceUnavailable as error:
            if not db.search(city=chosen_city, per_page=1)[1]:
                raise HTTPException(503, f"Источник данных не ответил ({error}).")

    rows, total = db.search(
        query=q,
        category=chosen_category,
        region=chosen_region,
        city=chosen_city,
        only_docs=onlyDocs,
        only_verified=onlyVerified,
        only_wholesale=onlyWholesale,
        sort=sort,
        page=page,
        per_page=perPage,
    )
    notes = {item["supplier_id"]: item["text"] for item in db.notes_of(owner)}
    answer = payload.page(rows, total, page, perPage, notes)
    answer["status"] = payload.status(index.state)
    answer["stats"] = db.stats()
    return answer


@app.get("/api/suppliers/{supplier_id:path}")
def api_supplier(supplier_id: str, request: Request, response: Response):
    row = db.get(supplier_id)
    if row is None:
        raise HTTPException(404, "Поставщик не найден")
    owner = user_id(request, response)
    notes = {item["supplier_id"]: item["text"] for item in db.notes_of(owner)}
    return payload.card(row, notes)


@app.get("/api/notes")
def api_notes(owner: str = Depends(user_id)):
    return [
        {"supplierId": item["supplier_id"], "text": item["text"], "updatedAt": item["updated_at"]}
        for item in db.notes_of(owner)
    ]


@app.post("/api/notes")
def api_save_note(note: NoteIn, owner: str = Depends(user_id)):
    if db.get(note.supplierId) is None:
        raise HTTPException(404, "Поставщик не найден")
    text = note.text.strip()[:2000]
    if not text:
        db.delete_note(owner, note.supplierId)
        return {"supplierId": note.supplierId, "text": "", "updatedAt": 0}
    saved = db.save_note(owner, note.supplierId, text)
    return {
        "supplierId": saved["supplier_id"],
        "text": saved["text"],
        "updatedAt": saved["updated_at"],
    }


@app.delete("/api/notes/{supplier_id:path}")
def api_delete_note(supplier_id: str, owner: str = Depends(user_id)):
    db.delete_note(owner, supplier_id)
    return {"ok": True}


@app.post("/api/compare/recommend")
def api_recommend(body: CompareIn, owner: str = Depends(user_id)):
    rows = db.get_many(body.ids[:6])
    if not rows:
        return {"bestId": "", "cheapestId": "", "text": ""}

    notes = {item["supplier_id"]: item["text"] for item in db.notes_of(owner)}
    cards = [payload.card(row, notes) for row in rows]
    best = max(cards, key=lambda item: item["score"])
    with_moq = [item for item in cards if item.get("moqValue")]
    cheapest = min(with_moq, key=lambda item: item["moqValue"]) if with_moq else None
    return {
        "bestId": best["id"],
        "cheapestId": cheapest["id"] if cheapest else "",
        "text": _recommendation(best, cheapest, cards),
    }


def _recommendation(best: dict, cheapest: dict | None, cards: list[dict]) -> str:
    contacts = _contacts_of(best)
    text = (
        f"Начать разговор стоит с «{best['name']}»: готовность к контакту {best['score']}%"
        f"{', ' + best['verdict'].lower() if best['verdict'] else ''}, {contacts}."
    )
    if best["certs"]:
        text += f" Документы: {', '.join(best['certs'][:3])}."
    if cheapest and cheapest["id"] != best["id"]:
        text += (
            f" Низкий порог входа — у «{cheapest['name']}»: минимальный заказ {cheapest['moq']}."
        )
    backup = next((item for item in cards if item["id"] != best["id"]), None)
    if not cheapest and backup:
        text += (
            f" Запасной вариант — «{backup['name']}»: {backup['score']}%, {_contacts_of(backup)}."
        )
    missing = [item["name"] for item in cards if not item["phone"] and not item["email"]]
    if missing:
        text += f" Без контактов в источниках: {', '.join(missing)}."
    return text


def _contacts_of(card: dict) -> str:
    found = [
        "телефон" if card["phone"] else "",
        "почта" if card["email"] else "",
        "сайт" if card["site"] and card["site"] != payload.NO_SITE else "",
    ]
    found = [item for item in found if item]
    return f"есть {', '.join(found)}" if found else "контактов в источниках нет"


def _admin(token: str) -> None:
    if not ADMIN_TOKEN or token != ADMIN_TOKEN:
        raise HTTPException(403, "Нужен ADMIN_TOKEN")


@app.post("/api/admin/verify")
def api_verify(
    supplierId: str = Body(...),
    verified: bool = Body(True),
    token: str = Body(""),
):
    _admin(token)
    if not db.set_verified(supplierId, verified, "проверено менеджером"):
        raise HTTPException(404, "Поставщик не найден")
    return {"ok": True}


@app.post("/api/admin/refresh")
async def api_refresh(city: str = Body(""), token: str = Body("")):
    _admin(token)
    found = catalog.city(city)
    if found is None:
        raise HTTPException(404, f"Не знаю город «{city}»")
    db.mark_refreshed(city, 0, "ручное обновление")
    with db._lock:
        db.connect().execute("DELETE FROM refreshes WHERE city=?", (city,))
        db.connect().commit()
    return {"indexed": await index.refresh_city(found)}


app.mount("/", WebFiles(directory=FRONTEND_DIR, html=True, check_dir=False))
