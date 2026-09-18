import asyncio
import time

import aiohttp
import catalog
import db
import domain
import scoring
from sources import active, egrul, website, wikidata

USER_AGENT = "ProviziaBot/1.0 (+https://github.com/zahar-pr/v2)"
REFRESH_TTL = 7 * 24 * 3600
RETRY_TTL = 600
PREWARM_PAUSE = 2.0
ENRICH_BATCH = 12
ENRICH_PARALLEL = 6
ENRICH_PAUSE = 4.0
EGRUL_BATCH = 8
EGRUL_PAUSE = 6.0

state = {
    "indexing": False,
    "city": "",
    "cities_done": 0,
    "cities_total": len(catalog.CITIES),
    "enriching": False,
    "enriched": 0,
    "egrul": 0,
    "errors": [],
}
_locks: dict[str, asyncio.Lock] = {}


def session() -> aiohttp.ClientSession:
    return aiohttp.ClientSession(
        headers={"User-Agent": USER_AGENT, "Accept-Language": "ru,en;q=0.8"},
        timeout=aiohttp.ClientTimeout(total=60),
    )


def is_fresh(city: str) -> bool:
    row = db.refresh_row(city)
    if row is None:
        return False
    waited = time.time() - row["refreshed_at"]
    if row["found"] > 0:
        return waited < REFRESH_TTL
    return waited < RETRY_TTL


async def ensure_city(city_name: str) -> int:
    city = catalog.city(city_name)
    if city is None:
        raise domain.PlaceNotFound(city_name)
    if is_fresh(city.name):
        return 0
    return await refresh_city(city)


async def refresh_city(city: catalog.City, shared=None) -> int:
    lock = _locks.setdefault(city.name, asyncio.Lock())
    async with lock:
        if is_fresh(city.name):
            return 0

        own = shared is None
        client = shared or session()
        state["city"] = city.name
        try:
            records: list[dict] = []
            failures: list[str] = []
            for source in active():
                try:
                    records += await source.collect(client, city)
                except Exception as error:
                    failures.append(f"{source.id}: {error}")

            if not records and failures:
                db.mark_refreshed(city.name, 0, "; ".join(failures))
                raise domain.SourceUnavailable(failures[0])

            merged = merge(records)
            db.save_indexed(merged)
            await _place_city(client, city)
            rescore(merged)
            db.mark_refreshed(city.name, len(merged), "; ".join(failures))
            return len(merged)
        finally:
            if own:
                await client.close()
            state["city"] = ""


async def _place_city(client, city: catalog.City) -> None:
    center = db.center_of(city.name)
    if center is None:
        for source in active():
            finder = getattr(source, "center", None)
            if finder is None:
                continue
            try:
                center = await finder(client, city.name)
                break
            except Exception:
                center = None
    if center:
        db.save_center(city.name, center[0], center[1])
        db.save_distances(city.name, center)


def merge(records: list[dict]) -> list[dict]:
    kept: dict[str, dict] = {}
    now = time.time()
    for record in records:
        record["name_key"] = domain.name_key(record["name"])
        record["checked_at"] = now
        key = f"{record['city']}|{record['name_key']}"
        first = kept.get(key)
        if first is None:
            kept[key] = record
            continue
        _absorb(first, record)
    return list(kept.values())


def _absorb(first: dict, extra: dict) -> None:
    first["branches"] = first.get("branches", 1) + 1
    first["phones"] = list(dict.fromkeys([*first.get("phones", []), *extra.get("phones", [])]))[:5]
    first["emails"] = list(dict.fromkeys([*first.get("emails", []), *extra.get("emails", [])]))[:3]
    first["website"] = first.get("website") or extra.get("website", "")
    first["hours"] = first.get("hours") or extra.get("hours", "")
    first["address"] = _longest(first.get("address", ""), extra.get("address", ""))
    first["wholesale"] = bool(first.get("wholesale") or extra.get("wholesale"))
    first["lat"] = first.get("lat") or extra.get("lat")
    first["lon"] = first.get("lon") or extra.get("lon")
    first["rating"] = first.get("rating") or extra.get("rating")
    first["reviews"] = first.get("reviews") or extra.get("reviews")
    first["sources"] = [*first.get("sources", []), *extra.get("sources", [])]

    cats = {item for item in (first.get("cats", "") + extra.get("cats", "")).split(",") if item}
    first["cats"] = "," + ",".join(sorted(cats)) + ","
    first["cats_titles"] = [catalog.title(item) for item in sorted(cats)]
    first["haystack"] = domain.haystack(first)


def _longest(first: str, second: str) -> str:
    return first if len(first) >= len(second) else second


def score_one(row: dict) -> dict:
    factors = scoring.evaluate(scoring.with_age(row))
    weights = scoring.weights_of(scoring.DEFAULT_PRESET)
    scores = {factor.id: factors[factor.id]["score"] for factor in scoring.FACTORS}
    scores["total"] = scoring.total(factors, weights)
    db.save_scores(row["id"], scores)
    return scores


def rescore(records: list[dict]) -> None:
    for record in records:
        saved = db.get(record["id"])
        if saved:
            score_one(saved)


async def prewarm() -> None:
    state["indexing"] = True
    state["cities_done"] = sum(1 for city in catalog.CITIES if is_fresh(city.name))
    try:
        async with session() as client:
            await backfill(client)
            for city in catalog.CITIES:
                if is_fresh(city.name):
                    continue
                try:
                    await refresh_city(city, client)
                except Exception as error:
                    state["errors"] = [*state["errors"][-4:], f"{city.name}: {error}"]
                state["cities_done"] += 1
                await asyncio.sleep(PREWARM_PAUSE)
    finally:
        state["indexing"] = False
        state["city"] = ""


async def backfill(client) -> None:
    for city in catalog.CITIES:
        if db.center_of(city.name) is None and db.refreshed_at(city.name):
            await _place_city(client, city)

    while True:
        pending = db.unscored(400)
        if not pending:
            return
        for row in pending:
            score_one(row)
        await asyncio.sleep(0)


async def enrich_forever() -> None:
    state["enriching"] = True
    try:
        async with session() as client:
            while True:
                pending = db.pending_enrichment(ENRICH_BATCH)
                if not pending:
                    await asyncio.sleep(30)
                    continue
                for chunk in _chunks(pending, ENRICH_PARALLEL):
                    await asyncio.gather(*(enrich_one(client, item) for item in chunk))
                    await asyncio.sleep(ENRICH_PAUSE)
    except asyncio.CancelledError:
        raise
    finally:
        state["enriching"] = False


async def enrich_one(client, supplier: dict) -> None:
    found: dict = {}
    confirmed = False
    try:
        from_site = await website.enrich(client, supplier)
        if from_site:
            confirmed = bool(from_site.pop("confirmed", False))
            found.update(from_site)

        from_wikidata = await wikidata.enrich(client, {**supplier, **found})
        if from_wikidata:
            confirmed = bool(from_wikidata.pop("confirmed", False)) or confirmed
            found.update(from_wikidata)
    except Exception:
        found = {}

    if not found:
        db.mark_enrich_failed(supplier["id"])
        return

    db.save_enrichment(supplier["id"], found)
    if confirmed:
        db.set_verified(supplier["id"], True, "контакты подтверждены на сайте поставщика")
    fresh = db.get(supplier["id"])
    if fresh:
        score_one(fresh)
    state["enriched"] += 1


async def egrul_forever() -> None:
    try:
        async with session() as client:
            while True:
                pending = db.pending_egrul(EGRUL_BATCH)
                if not pending:
                    await asyncio.sleep(120)
                    continue
                for supplier in pending:
                    await egrul_one(client, supplier)
                    await asyncio.sleep(EGRUL_PAUSE)
    except asyncio.CancelledError:
        raise


async def egrul_one(client, supplier: dict) -> None:
    city = catalog.city(supplier["city"])
    try:
        found = await egrul.lookup(client, supplier, city.code if city else "")
    except Exception:
        found = None

    db.mark_egrul_checked(supplier["id"])
    if not found:
        return

    db.save_enrichment(supplier["id"], found)
    fresh = db.get(supplier["id"])
    if fresh:
        score_one(fresh)
    state["egrul"] += 1


def _chunks(items: list, size: int):
    for start in range(0, len(items), size):
        yield items[start : start + size]
