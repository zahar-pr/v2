import asyncio

import catalog
import discovery
import store
from index import score_one, session, state
from sources import egrul, fns, website, wikidata, zoon

SITE_BATCH = 12
SITE_PARALLEL = 6
SITE_PAUSE = 4.0
EGRUL_BATCH = 8
EGRUL_PAUSE = 6.0
FNS_BATCH = 10
FNS_PAUSE = 3.0
REVIEWS_BATCH = 20
REVIEWS_PAUSE = 1.5
IDLE_PAUSE = 180
DISCOVER_FLOOR = 12000


async def sites_forever() -> None:
    state["enriching"] = True
    try:
        async with session() as client:
            while True:
                pending = store.pending_enrichment(SITE_BATCH)
                if not pending:
                    await asyncio.sleep(IDLE_PAUSE)
                    continue
                for group in _chunks(pending, SITE_PARALLEL):
                    await asyncio.gather(*(site_one(client, item) for item in group))
                    await asyncio.sleep(SITE_PAUSE)
    except asyncio.CancelledError:
        raise
    finally:
        state["enriching"] = False


async def site_one(client, supplier: dict) -> None:
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
        store.mark_enrich_failed(supplier["id"])
        return

    store.save_enrichment(supplier["id"], found)
    if confirmed:
        store.set_verified(supplier["id"], True, "контакты подтверждены на сайте поставщика")
    _rescore(supplier["id"])
    state["enriched"] += 1


async def egrul_forever() -> None:
    await _worker(store.pending_egrul, EGRUL_BATCH, EGRUL_PAUSE, egrul_one)


async def egrul_one(client, supplier: dict) -> None:
    city = catalog.city(supplier["city"])
    found = await _safe(egrul.lookup(client, supplier, city.code if city else ""))
    store.mark_egrul_checked(supplier["id"])
    if found:
        store.save_enrichment(supplier["id"], found)
        _rescore(supplier["id"])
        state["egrul"] += 1


async def reviews_forever() -> None:
    await _worker(store.pending_reviews, REVIEWS_BATCH, REVIEWS_PAUSE, reviews_one)


async def reviews_one(client, supplier: dict) -> None:
    found = await _safe(zoon.lookup(client, supplier))
    store.mark_reviews_checked(supplier["id"])
    if found:
        store.save_enrichment(supplier["id"], found)
        _rescore(supplier["id"])
        state["reviews"] += 1


async def fns_forever() -> None:
    try:
        async with session() as client:
            await warm_fns(client)
            if store.stats()["total"] < DISCOVER_FLOOR:
                await discovery.from_fns(client)
                await discovery.from_egrul(client)
            while True:
                pending = store.pending_fns(FNS_BATCH)
                if not pending:
                    await asyncio.sleep(IDLE_PAUSE * 2)
                    continue
                for supplier in pending:
                    await fns_one(client, supplier)
                    await asyncio.sleep(FNS_PAUSE)
    except asyncio.CancelledError:
        raise


async def fns_one(client, supplier: dict) -> None:
    city = catalog.city(supplier["city"])
    found = await _safe(fns.lookup(client, supplier, city.code if city else ""))
    store.mark_fns_checked(supplier["id"])
    if not found:
        return

    store.save_enrichment(supplier["id"], found)
    fresh = store.get(supplier["id"])
    if fresh and fresh.get("okved"):
        store.save_kind(
            supplier["id"],
            fns.kind_of(fresh["okved"]),
            _cats_with(fresh, fns.category_of(fresh["okved"])),
        )
    _rescore(supplier["id"])
    state["fns"] += 1


async def warm_fns(client) -> None:
    try:
        async with client.get(fns.HOME_URL) as answer:
            await answer.read()
    except Exception:
        pass


async def _worker(pending_of, batch: int, pause: float, handle) -> None:
    try:
        async with session() as client:
            while True:
                pending = pending_of(batch)
                if not pending:
                    await asyncio.sleep(IDLE_PAUSE * 2)
                    continue
                for supplier in pending:
                    await handle(client, supplier)
                    await asyncio.sleep(pause)
    except asyncio.CancelledError:
        raise


async def _safe(coroutine):
    try:
        return await coroutine
    except Exception:
        return None


def _rescore(supplier_id: str) -> None:
    fresh = store.get(supplier_id)
    if fresh:
        score_one(fresh)


def _cats_with(row: dict, category: str) -> str:
    known = {item for item in (row.get("cats") or "").split(",") if item}
    if category:
        known.add(category)
    return "," + ",".join(sorted(known)) + "," if known else ""


def _chunks(items: list, size: int):
    for start in range(0, len(items), size):
        yield items[start : start + size]
