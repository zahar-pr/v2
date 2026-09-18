import asyncio
import os
import uuid
from contextlib import asynccontextmanager

import catalog
import db
import domain
import index
import payload
import scoring
from fastapi import Body, Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import Response as RawResponse
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
CALL_LIMIT = 20
_workers: list[asyncio.Task] = []


@asynccontextmanager
async def lifespan(_app: FastAPI):
    db.connect()
    if os.environ.get("PROVIZIA_WORKERS", "1") == "1":
        _workers.append(asyncio.create_task(index.prewarm()))
        _workers.append(asyncio.create_task(index.enrich_forever()))
        _workers.append(asyncio.create_task(index.egrul_forever()))
        _workers.append(asyncio.create_task(index.fns_forever()))
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


class StatusIn(BaseModel):
    supplierId: str
    status: str = "new"


class CompareIn(BaseModel):
    ids: list[str] = []
    preset: str = scoring.DEFAULT_PRESET
    weights: str = ""


def user_id(request: Request, response: Response) -> str:
    found = request.cookies.get(COOKIE)
    if not found:
        found = uuid.uuid4().hex
        response.set_cookie(COOKIE, found, max_age=COOKIE_AGE, httponly=True, samesite="lax")
    return found


def _weights(preset: str, raw: str) -> dict:
    custom: dict = {}
    for chunk in (raw or "").split(","):
        name, _, value = chunk.partition(":")
        if name.strip() and value.strip().isdigit():
            custom[name.strip()] = int(value)
    return scoring.weights_of(preset, custom)


def _kinds(raw: str) -> tuple[str, ...]:
    known = {item["id"] for item in payload.KINDS}
    chosen = tuple(item for item in (raw or "").split(",") if item in known)
    return () if len(chosen) == len(known) else chosen


def _sources_meta() -> list[dict]:
    ready = {source.id for source in active()}
    listed = [
        {"id": source.id, "title": source.title, "active": source.id in ready}
        for source in SOURCES
    ]
    listed.append({"id": "website", "title": "Сайты поставщиков", "active": True})
    listed.append({"id": "egrul", "title": "ЕГРЮЛ (ФНС)", "active": True})
    listed.append({"id": "fns", "title": "ФНС: Прозрачный бизнес", "active": True})
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
    kinds: str = Query(""),
    onlyDocs: bool = Query(False),
    onlyVerified: bool = Query(False),
    onlyContacts: bool = Query(False),
    status: str = Query(""),
    preset: str = Query(scoring.DEFAULT_PRESET),
    weights: str = Query(""),
    sort: str = Query(catalog.SORTS[0]),
    page: int = Query(1, ge=1, le=500),
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

    used = _weights(preset, weights)
    rows, found, facets = db.search(
        query=q,
        category=chosen_category,
        region=chosen_region,
        city=chosen_city,
        kinds=_kinds(kinds),
        only_docs=onlyDocs,
        only_verified=onlyVerified,
        only_contacts=onlyContacts,
        status=status,
        user_id=owner,
        weights=used,
        sort=sort,
        page=page,
        per_page=perPage,
    )
    answer = payload.page(
        rows,
        found,
        page,
        perPage,
        _notes(owner),
        db.statuses_of(owner),
        used,
        preset,
    )
    answer["status"] = payload.status(index.state)
    answer["stats"] = db.stats()
    answer["facets"] = facets
    answer["pipeline"] = db.status_counts(owner)
    return answer


@app.get("/api/calllist")
def api_calllist(
    request: Request,
    response: Response,
    q: str = Query("", max_length=120),
    category: str = Query(catalog.ANY),
    region: str = Query(catalog.ANY_REGION_TITLE),
    city: str = Query(catalog.ANY_CITY_TITLE),
    kinds: str = Query(""),
    preset: str = Query(scoring.DEFAULT_PRESET),
    weights: str = Query(""),
    limit: int = Query(CALL_LIMIT, ge=1, le=50),
):
    owner = user_id(request, response)
    used = _weights(preset, weights)
    statuses = db.statuses_of(owner)
    rows, _, _ = db.search(
        query=q,
        category="" if category in ("", catalog.ANY) else category,
        region="" if region in ("", catalog.ANY, catalog.ANY_REGION_TITLE) else region,
        city="" if city in ("", catalog.ANY, catalog.ANY_CITY_TITLE) else city,
        kinds=_kinds(kinds),
        only_contacts=True,
        weights=used,
        sort=catalog.SORTS[0],
        page=1,
        per_page=limit * 2,
    )
    notes = _notes(owner)
    items = [
        payload.card(row, notes, statuses, used, rank=number + 1)
        for number, row in enumerate(rows)
        if statuses.get(row["id"], "new") not in ("rejected", "fit")
    ]
    return {"items": items[:limit], "weights": used, "preset": preset}


@app.get("/api/export.csv")
def api_export(
    request: Request,
    response: Response,
    q: str = Query("", max_length=120),
    category: str = Query(catalog.ANY),
    region: str = Query(catalog.ANY_REGION_TITLE),
    city: str = Query(catalog.ANY_CITY_TITLE),
    kinds: str = Query(""),
    onlyDocs: bool = Query(False),
    onlyVerified: bool = Query(False),
    onlyContacts: bool = Query(False),
    status: str = Query(""),
    preset: str = Query(scoring.DEFAULT_PRESET),
    weights: str = Query(""),
    sort: str = Query(catalog.SORTS[0]),
    limit: int = Query(300, ge=1, le=1000),
):
    owner = user_id(request, response)
    used = _weights(preset, weights)
    rows, _, _ = db.search(
        query=q,
        category="" if category in ("", catalog.ANY) else category,
        region="" if region in ("", catalog.ANY, catalog.ANY_REGION_TITLE) else region,
        city="" if city in ("", catalog.ANY, catalog.ANY_CITY_TITLE) else city,
        kinds=_kinds(kinds),
        only_docs=onlyDocs,
        only_verified=onlyVerified,
        only_contacts=onlyContacts,
        status=status,
        user_id=owner,
        weights=used,
        sort=sort,
        page=1,
        per_page=limit,
    )
    notes = _notes(owner)
    statuses = db.statuses_of(owner)
    cards = [
        payload.card(row, notes, statuses, used, rank=number + 1)
        for number, row in enumerate(rows)
    ]
    body = "\ufeff" + payload.to_csv(cards)
    return RawResponse(
        content=body.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="provizia.csv"'},
    )


@app.get("/api/suppliers/{supplier_id:path}")
def api_supplier(
    supplier_id: str,
    request: Request,
    response: Response,
    preset: str = Query(scoring.DEFAULT_PRESET),
    weights: str = Query(""),
):
    row = db.get(supplier_id)
    if row is None:
        raise HTTPException(404, "Поставщик не найден")
    owner = user_id(request, response)
    return payload.card(row, _notes(owner), db.statuses_of(owner), _weights(preset, weights))


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


@app.get("/api/pipeline")
def api_pipeline(owner: str = Depends(user_id)):
    return {"statuses": db.statuses_of(owner), "counts": db.status_counts(owner)}


@app.post("/api/pipeline")
def api_set_status(body: StatusIn, owner: str = Depends(user_id)):
    known = {item["id"] for item in payload.STATUSES}
    if body.status not in known:
        raise HTTPException(400, f"Неизвестный статус «{body.status}»")
    if db.get(body.supplierId) is None:
        raise HTTPException(404, "Поставщик не найден")
    saved = db.set_status(owner, body.supplierId, body.status)
    return {
        "supplierId": saved["supplier_id"],
        "status": saved["status"],
        "counts": db.status_counts(owner),
    }


@app.post("/api/compare/recommend")
def api_recommend(body: CompareIn, owner: str = Depends(user_id)):
    rows = db.get_many(body.ids[:6])
    if not rows:
        return {"bestId": "", "text": "", "cards": [], "diff": []}

    used = _weights(body.preset, body.weights)
    cards = [payload.card(row, _notes(owner), db.statuses_of(owner), used) for row in rows]
    ranked = sorted(cards, key=lambda item: -item["score"])
    best = ranked[0]
    runner = ranked[1] if len(ranked) > 1 else None

    return {
        "bestId": best["id"],
        "text": _recommendation(best, runner, ranked),
        "diff": _diff(best, runner),
        "weights": used,
    }


def _diff(best: dict, runner: dict | None) -> list[dict]:
    if runner is None:
        return []

    rows = []
    for position, (first, second) in enumerate(zip(best["factors"], runner["factors"])):
        gap = first["score"] - second["score"]
        if gap == 0:
            continue
        leader, behind = (best, runner) if gap > 0 else (runner, best)
        rows.append(
            {
                "factor": first["title"],
                "leader": leader["name"],
                "gap": abs(gap),
                "weight": first["weight"],
                "reason": (leader["factors"][position]["plus"] or [""])[0],
                "lack": (behind["factors"][position]["minus"] or [""])[0],
            }
        )
    return sorted(rows, key=lambda item: -item["gap"] * max(item["weight"], 1))[:4]


def _recommendation(best: dict, runner: dict | None, cards: list[dict]) -> str:
    text = f"Звонить первым — «{best['name']}»: {best['score']} из 100 по вашим приоритетам"
    strong = max(best["factors"], key=lambda item: item["score"] * max(item["weight"], 1))
    if strong["plus"]:
        text += f". Сильная сторона — {strong['title'].lower()}: {strong['plus'][0]}"
    if runner:
        gap = best["score"] - runner["score"]
        text += f". «{runner['name']}» отстаёт на {gap} {_points(gap)}"
    asks = best["ask"][:2]
    if asks:
        text += ". Что спросить в первом звонке: " + "; ".join(asks).lower()
    missing = [item["name"] for item in cards if not item["phone"] and not item["email"]]
    if missing:
        text += f". Без контактов в источниках: {', '.join(missing)}"
    return text + "."


def _points(n: int) -> str:
    if n % 10 == 1 and n % 100 != 11:
        return "пункт"
    if 2 <= n % 10 <= 4 and not 10 <= n % 100 < 20:
        return "пункта"
    return "пунктов"


def _notes(owner: str) -> dict:
    return {item["supplier_id"]: item["text"] for item in db.notes_of(owner)}


def _admin(token: str) -> None:
    if not ADMIN_TOKEN or token != ADMIN_TOKEN:
        raise HTTPException(403, "Нужен ADMIN_TOKEN")


@app.post("/api/admin/verify")
def api_verify(supplierId: str = Body(...), verified: bool = Body(True), token: str = Body("")):
    _admin(token)
    if not db.set_verified(supplierId, verified, "проверено менеджером"):
        raise HTTPException(404, "Поставщик не найден")
    row = db.get(supplierId)
    if row:
        index.score_one(row)
    return {"ok": True}


@app.post("/api/admin/refresh")
async def api_refresh(city: str = Body(""), token: str = Body("")):
    _admin(token)
    found = catalog.city(city)
    if found is None:
        raise HTTPException(404, f"Не знаю город «{city}»")
    with db._lock:
        db.connect().execute("DELETE FROM refreshes WHERE city=?", (city,))
        db.connect().commit()
    return {"indexed": await index.refresh_city(found)}


app.mount("/", WebFiles(directory=FRONTEND_DIR, html=True, check_dir=False))
