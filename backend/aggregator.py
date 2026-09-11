import asyncio
import re
import time

from catalog import Category
from domain import Supplier, is_food_related, rate
from sources import SOURCES

MAX_RESULTS = 10
CACHE_TTL = 3600
_cache: dict[str, tuple[float, list[Supplier]]] = {}


async def find(category: Category, place: str) -> list[Supplier]:
    cache_key = f"{category.id}|{place.lower()}"
    saved_at, cached = _cache.get(cache_key, (0.0, []))
    if time.time() - saved_at < CACHE_TTL:
        return _best(cached)
    found = _merge(await _ask_sources(category, place))
    _cache[cache_key] = (time.time(), found)
    return _best(found)


async def _ask_sources(category: Category, place: str) -> list[Supplier]:
    answers = await asyncio.gather(
        *(source.search(category, place) for source in SOURCES), return_exceptions=True
    )
    suppliers: list[Supplier] = []
    failures: list[Exception] = []
    for answer in answers:
        if isinstance(answer, Exception):
            failures.append(answer)
        else:
            suppliers += answer
    if not suppliers and failures:
        raise failures[0]
    return suppliers


def _merge(suppliers: list[Supplier]) -> list[Supplier]:
    merged: dict[str, Supplier] = {}
    for supplier in suppliers:
        if not is_food_related(supplier.name):
            continue
        key = re.sub(r"[^a-zа-я0-9]", "", supplier.name.lower())
        kept = merged.setdefault(key, supplier)
        if kept is not supplier:
            _absorb(kept, supplier)
    return list(merged.values())


def _absorb(kept: Supplier, extra: Supplier) -> None:
    kept.branches += 1
    kept.phones = list(dict.fromkeys(kept.phones + extra.phones))
    kept.emails = list(dict.fromkeys(kept.emails + extra.emails))
    kept.website = kept.website or extra.website
    kept.address = kept.address or extra.address
    kept.hours = kept.hours or extra.hours
    kept.wholesale = kept.wholesale or extra.wholesale


def _best(suppliers: list[Supplier]) -> list[Supplier]:
    for supplier in suppliers:
        supplier.rating = rate(supplier)
    return sorted(suppliers, key=lambda supplier: -supplier.rating.score)[:MAX_RESULTS]
