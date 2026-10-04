import asyncio
import os
from contextlib import asynccontextmanager

import catalog
import db
import domain
import enrich
import index
import payload
import store
import team
import web
import workspace
from fastapi import Body, Depends, FastAPI, HTTPException, Query
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import Response as RawResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sources import SOURCES, active

FRONTEND_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "dist"
)
CALL_LIMIT = 20
COMMENT_LIMIT = 20
EXPORT_LIMIT = 300
_workers: list[asyncio.Task] = []


@asynccontextmanager
async def lifespan(_app: FastAPI):
    db.connect()
    if os.environ.get("PROVIZIA_WORKERS", "1") == "1":
        for worker in (
            index.prewarm,
            enrich.sites_forever,
            enrich.egrul_forever,
            enrich.fns_forever,
            enrich.reviews_forever,
        ):
            _workers.append(asyncio.create_task(worker()))
    yield
    for task in _workers:
        task.cancel()


app = FastAPI(title="Провизия — поиск поставщиков продуктов питания", lifespan=lifespan)
app.add_middleware(GZipMiddleware, minimum_size=800)


class WebFiles(StaticFiles):
    def file_response(self, full_path, *args, **kwargs):
        answer = super().file_response(full_path, *args, **kwargs)
        path = str(full_path)
        if path.endswith(".html"):
            answer.headers["Cache-Control"] = "no-store"
        elif "/assets/" in path:
            answer.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        else:
            answer.headers["Cache-Control"] = "public, max-age=604800"
        return answer


class NoteIn(BaseModel):
    supplierId: str
    text: str = ""


class StatusIn(BaseModel):
    supplierId: str
    status: str = "new"


class CheckIn(BaseModel):
    supplierId: str
    question: str
    done: bool = True


class CommentIn(BaseModel):
    supplierId: str
    text: str = ""
    rating: int | None = None
    author: str = ""


class ProfileIn(BaseModel):
    name: str = ""


class CompareIn(BaseModel):
    ids: list[str] = []
    preset: str = "balanced"
    weights: str = ""


@app.get("/api/meta")
def api_meta():
    answer = payload.meta(store.stats(), index.state, _sources(), _defaults())
    showcase = store.get_many(store.showcase())
    answer["showcase"] = web.cards(showcase, web.weights_of("", ""))
    return answer


@app.get("/api/workspace")
def api_workspace():
    """Кабинет Goulash Tech: проекты сетей, воронка и последние действия команды."""
    return workspace.overview()


@app.get("/api/status")
def api_status():
    return {"stats": store.stats(), "status": payload.status(index.state)}


@app.get("/api/suppliers")
async def api_suppliers(
    owner: str = Depends(web.user_id),
    chosen: web.Filters = web.Query_,
    page: int = Query(1, ge=1, le=500),
    perPage: int = Query(web.PER_PAGE, ge=1, le=web.MAX_PER_PAGE),
):
    await _ensure_city(chosen.city)
    rows, found, facets = chosen.search(page, perPage)

    answer = payload.page(
        rows,
        found,
        page,
        perPage,
        web.notes(),
        team.statuses_of(),
        chosen.weights,
        chosen.preset,
        checks=web.checks(rows),
        city=chosen.city,
    )
    if not found:
        answer["relax"] = store.relax_options(chosen.as_dict(), web.RELAX_LABELS)
    answer["status"] = payload.status(index.state)
    answer["stats"] = store.stats()
    answer["facets"] = facets
    answer["pipeline"] = team.status_counts()
    return answer


@app.get("/api/calllist")
def api_calllist(
    owner: str = Depends(web.user_id),
    chosen: web.Filters = web.Query_,
    limit: int = Query(CALL_LIMIT, ge=1, le=60),
):
    statuses = team.statuses_of()
    working = [key for key, item in statuses.items() if item["status"] == "calling"]

    chosen.only_contacts = True
    chosen.status = ""
    rows, _, _ = chosen.search(1, limit * 3)
    suggest = [
        row for row in rows if (statuses.get(row["id"]) or {}).get("status", "new") == "new"
    ]

    return {
        "working": web.by_score(store.get_many(working), chosen.weights, chosen.city),
        "suggest": web.by_score(suggest[: limit * 2], chosen.weights, chosen.city)[:limit],
        "weights": chosen.weights,
        "preset": chosen.preset,
    }


@app.get("/api/export.csv")
def api_export(
    owner: str = Depends(web.user_id),
    chosen: web.Filters = web.Query_,
    limit: int = Query(EXPORT_LIMIT, ge=1, le=1000),
):
    rows, _, _ = chosen.search(1, limit)
    body = "﻿" + payload.to_csv(web.cards(rows, chosen.weights, chosen.city))
    return RawResponse(
        content=body.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="provizia.csv"'},
    )


@app.get("/api/similar")
def api_similar(
    id: str = Query("", max_length=200),
    owner: str = Depends(web.user_id),
    chosen: web.Filters = web.Query_,
    limit: int = Query(4, ge=1, le=8),
):
    """Альтернативы для досье: тот же продукт, та же география, без замечаний."""
    row = store.get(id)
    if row is None:
        raise HTTPException(404, "Поставщик не найден")
    rows = store.similar(row, chosen.weights, limit)
    return {"items": web.cards(rows, chosen.weights, chosen.city)}


@app.get("/api/suppliers/{supplier_id:path}")
def api_supplier(
    supplier_id: str,
    owner: str = Depends(web.user_id),
    chosen: web.Filters = web.Query_,
):
    row = store.get(supplier_id)
    if row is None:
        raise HTTPException(404, "Поставщик не найден")
    return payload.card(
        row,
        web.notes(),
        team.statuses_of(),
        chosen.weights,
        checks={supplier_id: team.checks_of(supplier_id)},
        city=chosen.city,
    )


@app.get("/api/notes")
def api_notes():
    return [
        {
            "supplierId": item["supplier_id"],
            "text": item["text"],
            "author": item["author"],
            "updatedAt": item["updated_at"],
        }
        for item in team.notes_of()
    ]


@app.post("/api/notes")
def api_save_note(note: NoteIn, owner: str = Depends(web.user_id)):
    _require_supplier(note.supplierId)
    text = note.text.strip()[:2000]
    if not text:
        team.delete_note(note.supplierId)
        return {"supplierId": note.supplierId, "text": "", "author": "", "updatedAt": 0}

    saved = team.save_note(owner, team.profile_of(owner), note.supplierId, text)
    return {
        "supplierId": saved["supplier_id"],
        "text": saved["text"],
        "author": saved["author"],
        "updatedAt": saved["updated_at"],
    }


@app.delete("/api/notes/{supplier_id:path}")
def api_delete_note(supplier_id: str):
    team.delete_note(supplier_id)
    return {"ok": True}


@app.get("/api/checks/{supplier_id:path}")
def api_checks(supplier_id: str):
    return {"done": team.checks_of(supplier_id)}


@app.post("/api/checks")
def api_set_check(body: CheckIn, owner: str = Depends(web.user_id)):
    _require_supplier(body.supplierId)
    team.set_check(body.supplierId, body.question.strip()[:200], body.done, team.profile_of(owner))
    return {"done": team.checks_of(body.supplierId)}


@app.get("/api/pipeline")
def api_pipeline():
    return {"statuses": team.statuses_of(), "counts": team.status_counts()}


@app.post("/api/pipeline")
def api_set_status(body: StatusIn, owner: str = Depends(web.user_id)):
    if body.status not in {item["id"] for item in payload.STATUSES}:
        raise HTTPException(400, f"Неизвестный статус «{body.status}»")
    _require_supplier(body.supplierId)
    saved = team.set_status(owner, team.profile_of(owner), body.supplierId, body.status)
    return {
        "supplierId": saved["supplier_id"],
        "status": saved["status"],
        "counts": team.status_counts(),
    }


@app.get("/api/profile")
def api_profile(owner: str = Depends(web.user_id)):
    return {"name": team.profile_of(owner)}


@app.post("/api/profile")
def api_save_profile(body: ProfileIn, owner: str = Depends(web.user_id)):
    return {"name": team.save_profile(owner, body.name.strip()[:60])}


@app.get("/api/comments/{supplier_id:path}")
def api_comments(supplier_id: str, owner: str = Depends(web.user_id)):
    return {
        "items": [payload.comment(row, owner) for row in team.comments_of(supplier_id)],
        "author": team.profile_of(owner),
    }


@app.post("/api/comments")
def api_add_comment(body: CommentIn, owner: str = Depends(web.user_id)):
    _require_supplier(body.supplierId)

    text = body.text.strip()[:2000]
    if not text:
        raise HTTPException(400, "Комментарий пустой")
    if body.rating is not None and not 1 <= body.rating <= 5:
        raise HTTPException(400, "Оценка должна быть от 1 до 5")
    if team.comments_by(owner, body.supplierId) >= COMMENT_LIMIT:
        raise HTTPException(429, f"Не больше {COMMENT_LIMIT} комментариев к одному поставщику")

    author = (body.author or "").strip()[:60]
    if author:
        team.save_profile(owner, author)
    else:
        author = team.profile_of(owner)

    saved = team.add_comment(owner, body.supplierId, author, text, body.rating)
    _rescore(body.supplierId)
    return payload.comment(saved, owner)


@app.delete("/api/comments/{comment_id}")
def api_delete_comment(comment_id: int, owner: str = Depends(web.user_id)):
    supplier_id = team.delete_comment(owner, comment_id)
    if not supplier_id:
        raise HTTPException(404, "Комментарий не найден")
    _rescore(supplier_id)
    return {"ok": True}


@app.post("/api/compare/recommend")
def api_recommend(body: CompareIn, owner: str = Depends(web.user_id)):
    rows = store.get_many(body.ids[:6])
    if not rows:
        return {"bestId": "", "text": "", "diff": []}

    used = web.weights_of(body.preset, body.weights)
    chosen = web.cards(rows, used)
    ranked = sorted(chosen, key=lambda item: -item["score"])
    best = ranked[0]
    runner = ranked[1] if len(ranked) > 1 else None
    return {
        "bestId": best["id"],
        "text": web.recommendation(best, runner, ranked),
        "diff": web.factor_diff(best, runner),
        "weights": used,
    }


@app.post("/api/admin/verify")
def api_verify(supplierId: str = Body(...), verified: bool = Body(True), token: str = Body("")):
    web.require_admin(token)
    if not store.set_verified(supplierId, verified, "проверено менеджером"):
        raise HTTPException(404, "Поставщик не найден")
    _rescore(supplierId)
    return {"ok": True}


@app.post("/api/admin/refresh")
async def api_refresh(city: str = Body(""), token: str = Body("")):
    web.require_admin(token)
    found = catalog.city(city)
    if found is None:
        raise HTTPException(404, f"Не знаю город «{city}»")
    store.forget_city(city)
    return {"indexed": await index.refresh_city(found)}


async def _ensure_city(city: str) -> None:
    if not city:
        return
    try:
        await index.ensure_city(city)
    except domain.PlaceNotFound:
        raise HTTPException(404, f"Не нашёл город «{city}»")
    except domain.SourceUnavailable as error:
        if not store.search(city=city, per_page=1)[1]:
            raise HTTPException(503, f"Источник данных не ответил ({error}).")


def _require_supplier(supplier_id: str) -> None:
    if store.get(supplier_id) is None:
        raise HTTPException(404, "Поставщик не найден")


def _rescore(supplier_id: str) -> None:
    row = store.get(supplier_id)
    if row:
        index.score_one(row)


def _defaults() -> dict:
    """Первый экран открывается там, где работает закупщик.

    Сервис сделан для Goulash Tech, база компании — Екатеринбург, поэтому выдача
    стартует по нему: видно и местные производства, и федеральных поставщиков,
    которые туда довезут. Категория остаётся «все» — сужать за пользователя
    незачем, он выберет продукт сам или возьмёт готовый проект в кабинете.
    """
    found = store.best_defaults()
    home = workspace.BASE_CITY
    if catalog.city(home) and store.count_for(city=home):
        found["region"] = catalog.region_of(home)
        found["city"] = home
    found["category"] = catalog.ANY
    return found


def _sources() -> list[dict]:
    ready = {source.id for source in active()}
    listed = [
        {"id": source.id, "title": source.title, "active": source.id in ready}
        for source in SOURCES
    ]
    for source_id, title in (
        ("website", "Сайты поставщиков"),
        ("egrul", "ЕГРЮЛ (ФНС)"),
        ("fns", "ФНС: Прозрачный бизнес"),
        ("wikidata", "Wikidata"),
        ("zoon", "Отзывы на Zoon"),
    ):
        listed.append({"id": source_id, "title": title, "active": True})
    return listed


@app.middleware("http")
async def hide_api_from_search(request, call_next):
    """JSON-ответы в поиск не нужны: сам сайт индексируется, его данные — нет."""
    answer = await call_next(request)
    if request.url.path.startswith("/api/"):
        answer.headers["X-Robots-Tag"] = "noindex"
    return answer


app.mount("/", WebFiles(directory=FRONTEND_DIR, html=True, check_dir=False))
