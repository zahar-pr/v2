import asyncio
import time

import aiohttp
import catalog
import db
import domain
import scoring
from sources import active, egrul, fns, website, wikidata

USER_AGENT = "ProviziaBot/1.0 (+https://github.com/zahar-pr/v2)"
REFRESH_TTL = 7 * 24 * 3600
RETRY_TTL = 600
PREWARM_PAUSE = 2.0
ENRICH_BATCH = 12
ENRICH_PARALLEL = 6
ENRICH_PAUSE = 4.0
EGRUL_BATCH = 8
EGRUL_PAUSE = 6.0
FNS_BATCH = 10
FNS_PAUSE = 3.0
DISCOVER_PAGES = 3
DISCOVER_FLOOR = 6000

state = {
    "indexing": False,
    "city": "",
    "cities_done": 0,
    "cities_total": len(catalog.CITIES),
    "enriching": False,
    "enriched": 0,
    "egrul": 0,
    "fns": 0,
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


async def fns_forever() -> None:
    try:
        async with session() as client:
            await _warm_fns(client)
            if db.stats()["total"] < DISCOVER_FLOOR:
                await discover_registry(client)
                await discover_egrul(client)
            while True:
                pending = db.pending_fns(FNS_BATCH)
                if not pending:
                    await asyncio.sleep(180)
                    continue
                for supplier in pending:
                    await fns_one(client, supplier)
                    await asyncio.sleep(FNS_PAUSE)
    except asyncio.CancelledError:
        raise


async def _warm_fns(client) -> None:
    try:
        async with client.get(fns.HOME_URL) as response:
            await response.read()
    except Exception:
        pass


async def fns_one(client, supplier: dict) -> None:
    city = catalog.city(supplier["city"])
    try:
        found = await fns.lookup(client, supplier, city.code if city else "")
    except Exception:
        found = None

    db.mark_fns_checked(supplier["id"])
    if not found:
        return

    db.save_enrichment(supplier["id"], found)
    fresh = db.get(supplier["id"])
    if fresh:
        if not fresh.get("okved"):
            score_one(fresh)
            return
        kind = fns.kind_of(fresh["okved"])
        cats = _cats_with(fresh, fns.category_of(fresh["okved"]))
        db.save_kind(supplier["id"], kind, cats)
        score_one(db.get(supplier["id"]) or fresh)
    state["fns"] += 1


def _cats_with(row: dict, category: str) -> str:
    known = {item for item in (row.get("cats") or "").split(",") if item}
    if category:
        known.add(category)
    return "," + ",".join(sorted(known)) + "," if known else ""


async def discover_registry(client) -> int:
    added = 0
    for query in fns.DISCOVERY_QUERIES:
        for page in range(1, DISCOVER_PAGES + 1):
            try:
                rows = await fns.discover(client, "", query, page)
            except Exception:
                rows = []
            if not rows:
                break
            added += _save_registry(rows)
            state["found"] = added
            await asyncio.sleep(FNS_PAUSE)
    return added


def _save_registry(rows: list[dict]) -> int:
    fresh: list[dict] = []
    for row in rows:
        record = _registry_record(row)
        if record is None:
            continue
        known = db.find_by_inn(record["inn"]) or db.find_by_key(record["name_key"])
        if known:
            db.save_enrichment(
                known["id"],
                {
                    "inn": record["inn"],
                    "ogrn": record["ogrn"],
                    "okved": record["okved"],
                    "okved_name": record["okved_name"],
                    "legal_name": record["legal_name"],
                    "legal_status": record["legal_status"],
                    "legal_active": record["legal_active"],
                    "founded": record["founded"],
                    "years": record["years"],
                    "sources": record["sources"],
                },
            )
            row_now = db.get(known["id"])
            if row_now:
                score_one(row_now)
            continue
        fresh.append(record)

    if fresh:
        db.save_indexed(fresh)
        for record in fresh:
            db.save_enrichment(
                record["id"],
                {
                    "inn": record["inn"],
                    "ogrn": record["ogrn"],
                    "okved": record["okved"],
                    "okved_name": record["okved_name"],
                    "legal_name": record["legal_name"],
                    "legal_status": record["legal_status"],
                    "legal_active": record["legal_active"],
                    "founded": record["founded"],
                    "years": record["years"],
                    "sources": record["sources"],
                    "haystack": record["haystack"],
                },
            )
            saved = db.get(record["id"])
            if saved:
                score_one(saved)
    return len(fresh)


def _registry_record(row: dict) -> dict | None:
    inn = (row.get("inn") or "").strip()
    name = fns.display_name(row)
    okved = (row.get("okved2main") or "").strip()
    if not inn or not name or not okved:
        return None

    kind = fns.kind_of(okved)
    if kind == "retail":
        return None

    category = fns.category_of(okved)
    area = catalog.pretty_area(row.get("regionname") or "")
    founded = None
    parts = (row.get("dtreg") or "").split(".")
    if len(parts) == 3 and parts[2].isdigit():
        founded = int(parts[2])

    record = {
        "id": f"fns:{inn}",
        "name": name,
        "name_key": domain.name_key(name),
        "city": "",
        "area": area,
        "region": catalog.region_by_area(row.get("regionname") or ""),
        "cats": f",{category}," if category else ",wholesale,",
        "cats_titles": [catalog.title(category)] if category else [],
        "kind": (row.get("okved2mainname") or "")[:60],
        "kind_tag": f"okved={okved}",
        "kind_class": kind,
        "address": area,
        "phones": [],
        "emails": [],
        "socials": [],
        "website": "",
        "hours": "",
        "wholesale": kind in ("producer", "wholesale"),
        "branches": 1,
        "lat": None,
        "lon": None,
        "distance_km": None,
        "source": fns.CARD_URL.format(token=row.get("token") or ""),
        "source_title": "ФНС: Прозрачный бизнес",
        "sources": [
            {
                "id": "fns",
                "title": "ФНС: Прозрачный бизнес",
                "url": fns.CARD_URL.format(token=row.get("token") or ""),
            }
        ],
        "checked_at": time.time(),
        "inn": inn,
        "ogrn": (row.get("ogrn") or "").strip(),
        "okved": okved,
        "okved_name": row.get("okved2mainname") or "",
        "legal_name": row.get("namep") or name,
        "legal_status": row.get("sulst_name_ex") or "",
        "legal_active": 0 if row.get("pr_liq") == "1" else 1,
        "founded": founded,
        "years": (
            f"{2026 - founded} {fns._plural(2026 - founded)} (с {founded})" if founded else ""
        ),
    }
    record["haystack"] = " ".join(
        [domain.haystack(record), okved, record["okved_name"], area, record["legal_name"]]
    ).lower()[:2000]
    return record


async def discover_egrul(client, pages: int = 2) -> int:
    added = 0
    for query, category, kind in egrul.DISCOVERY:
        for page in range(1, pages + 1):
            try:
                rows = await egrul.discover(client, query, "", page)
            except Exception:
                rows = []
            if not rows:
                break
            added += _save_egrul(rows, category, kind)
            state["found"] = added
            await asyncio.sleep(2.5)
    return added


def _save_egrul(rows: list[dict], category: str, kind: str) -> int:
    fresh: list[dict] = []
    for row in rows:
        record = _egrul_record(row, category, kind)
        if record is None:
            continue
        if db.find_by_inn(record["inn"]) or db.find_by_key(record["name_key"]):
            continue
        fresh.append(record)

    if fresh:
        db.save_indexed(fresh)
        for record in fresh:
            db.save_enrichment(
                record["id"],
                {
                    "inn": record["inn"],
                    "ogrn": record["ogrn"],
                    "legal_name": record["legal_name"],
                    "legal_status": record["legal_status"],
                    "legal_active": record["legal_active"],
                    "manager": record["manager"],
                    "founded": record["founded"],
                    "years": record["years"],
                    "sources": record["sources"],
                    "haystack": record["haystack"],
                },
            )
            saved = db.get(record["id"])
            if saved:
                score_one(saved)
    return len(fresh)


def _egrul_record(row: dict, category: str, kind: str) -> dict | None:
    inn = (row.get("i") or "").strip()
    name = egrul.display_name(row)
    if not inn or len(name) < 3:
        return None

    closed = bool(row.get("e") and row.get("e") != row.get("r"))
    area = catalog.pretty_area((row.get("rn") or "").replace("Г.", "").split("(")[0].strip())
    founded = None
    parts = (row.get("r") or "").split(".")
    if len(parts) == 3 and parts[2].isdigit():
        founded = int(parts[2])

    url = egrul.CARD_URL.format(query=inn)
    record = {
        "id": f"egrul:{inn}",
        "name": name,
        "name_key": domain.name_key(name),
        "city": "",
        "area": area,
        "region": catalog.region_by_area(area),
        "cats": f",{category},",
        "cats_titles": [catalog.title(category)],
        "kind": catalog.title(category),
        "kind_tag": "egrul",
        "kind_class": kind,
        "address": area,
        "phones": [],
        "emails": [],
        "socials": [],
        "website": "",
        "hours": "",
        "wholesale": kind in ("producer", "wholesale"),
        "branches": 1,
        "lat": None,
        "lon": None,
        "distance_km": None,
        "source": url,
        "source_title": "ЕГРЮЛ (ФНС)",
        "sources": [{"id": "egrul", "title": "ЕГРЮЛ (ФНС)", "url": url}],
        "checked_at": time.time(),
        "inn": inn,
        "ogrn": (row.get("o") or "").strip(),
        "legal_name": row.get("n") or name,
        "legal_status": "Есть запись о прекращении" if closed else "Действующая организация",
        "legal_active": 0 if closed else 1,
        "manager": egrul._head(row.get("g") or ""),
        "founded": founded,
        "years": (
            f"{2026 - founded} {egrul._plural(2026 - founded)} (с {founded})" if founded else ""
        ),
    }
    record["haystack"] = " ".join([domain.haystack(record), area, record["legal_name"]]).lower()[
        :2000
    ]
    return record
