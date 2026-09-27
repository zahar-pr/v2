import asyncio
import time

import aiohttp
import catalog
import domain
import scoring
import store
from sources import active

USER_AGENT = "ProviziaBot/1.0 (+https://github.com/zahar-pr/v2)"
REFRESH_TTL = 7 * 24 * 3600
RETRY_TTL = 600
PREWARM_PAUSE = 2.0
SCORE_BATCH = 400

state = {
    "indexing": False,
    "city": "",
    "cities_done": 0,
    "cities_total": len(catalog.CITIES),
    "enriching": False,
    "enriched": 0,
    "egrul": 0,
    "fns": 0,
    "reviews": 0,
    "found": 0,
    "errors": [],
}
_locks: dict[str, asyncio.Lock] = {}


def session() -> aiohttp.ClientSession:
    return aiohttp.ClientSession(
        headers={"User-Agent": USER_AGENT, "Accept-Language": "ru,en;q=0.8"},
        timeout=aiohttp.ClientTimeout(total=60),
    )


def is_fresh(city: str) -> bool:
    row = store.refresh_row(city)
    if row is None:
        return False
    waited = time.time() - row["refreshed_at"]
    return waited < (REFRESH_TTL if row["found"] > 0 else RETRY_TTL)


async def ensure_city(city_name: str) -> int:
    city = catalog.city(city_name)
    if city is None:
        raise domain.PlaceNotFound(city_name)
    return 0 if is_fresh(city.name) else await refresh_city(city)


async def refresh_city(city: catalog.City, shared=None) -> int:
    lock = _locks.setdefault(city.name, asyncio.Lock())
    async with lock:
        if is_fresh(city.name):
            return 0

        client = shared or session()
        state["city"] = city.name
        try:
            records, failures = await _collect(client, city)
            if not records and failures:
                store.mark_refreshed(city.name, 0, "; ".join(failures))
                raise domain.SourceUnavailable(failures[0])

            started = time.time()
            merged = merge(records)
            store.save_indexed(merged)
            store.prune_city(city.name, started)
            await _place_city(client, city)
            rescore(merged)
            store.mark_refreshed(city.name, len(merged), "; ".join(failures))
            return len(merged)
        finally:
            if shared is None:
                await client.close()
            state["city"] = ""


async def _collect(client, city: catalog.City) -> tuple[list[dict], list[str]]:
    records: list[dict] = []
    failures: list[str] = []
    for source in active():
        try:
            records += await source.collect(client, city)
        except Exception as error:
            failures.append(f"{source.id}: {error}")
    return records, failures


async def _place_city(client, city: catalog.City) -> None:
    center = store.center_of(city.name)
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
        store.save_center(city.name, center[0], center[1])
        store.save_distances(city.name, center)


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
        else:
            _absorb(first, record)
    return list(kept.values())


def _absorb(first: dict, extra: dict) -> None:
    first["branches"] = first.get("branches", 1) + 1
    first["phones"] = _join(first.get("phones"), extra.get("phones"), 5)
    first["emails"] = _join(first.get("emails"), extra.get("emails"), 3)
    first["socials"] = _join(first.get("socials"), extra.get("socials"), 4)
    first["sources"] = [*first.get("sources", []), *extra.get("sources", [])]
    for field in ("website", "hours", "lat", "lon", "rating", "reviews"):
        first[field] = first.get(field) or extra.get(field)
    first["address"] = max(first.get("address", ""), extra.get("address", ""), key=len)
    first["wholesale"] = bool(first.get("wholesale") or extra.get("wholesale"))

    cats = {item for item in (first.get("cats", "") + extra.get("cats", "")).split(",") if item}
    first["cats"] = "," + ",".join(sorted(cats)) + ","
    first["cats_titles"] = [catalog.title(item) for item in sorted(cats)]
    first["haystack"] = domain.haystack(first)


def _join(first, second, limit: int) -> list:
    return list(dict.fromkeys([*(first or []), *(second or [])]))[:limit]


def score_one(row: dict) -> dict:
    factors = scoring.evaluate(scoring.with_age(row))
    scores = {factor.id: factors[factor.id]["score"] for factor in scoring.FACTORS}
    scores["total"] = scoring.total(factors, scoring.weights_of(scoring.DEFAULT_PRESET))
    store.save_scores(row["id"], scores)
    return scores


def rescore(records: list[dict]) -> None:
    for record in records:
        saved = store.get(record["id"])
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
        if store.center_of(city.name) is None and store.refreshed_at(city.name):
            await _place_city(client, city)

    while True:
        pending = store.unscored(SCORE_BATCH)
        if not pending:
            return
        for row in pending:
            score_one(row)
        await asyncio.sleep(0)
