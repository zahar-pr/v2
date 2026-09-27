import asyncio
import time

import catalog
import domain
import store
from index import score_one, state
from sources import egrul, fns

PAGES = 3
FNS_PAUSE = 3.0
EGRUL_PAUSE = 2.5
LEGAL_FIELDS = (
    "inn",
    "ogrn",
    "okved",
    "okved_name",
    "legal_name",
    "legal_status",
    "legal_active",
    "manager",
    "founded",
    "years",
    "sources",
)


async def from_fns(client, pages: int = PAGES) -> int:
    added = 0
    for query in fns.DISCOVERY_QUERIES:
        for page in range(1, pages + 1):
            rows = await _safe(fns.discover(client, "", query, page))
            if not rows:
                break
            added += save([_from_fns(row) for row in rows])
            state["found"] = added
            await asyncio.sleep(FNS_PAUSE)
    return added


async def from_egrul(client, pages: int = PAGES) -> int:
    added = 0
    for query, category, kind in egrul.DISCOVERY:
        for page in range(1, pages + 1):
            rows = await _safe(egrul.discover(client, query, "", page))
            if not rows:
                break
            added += save([_from_egrul(row, category, kind) for row in rows])
            state["found"] = added
            await asyncio.sleep(EGRUL_PAUSE)
    return added


def save(records: list[dict | None]) -> int:
    fresh = []
    for record in records:
        if record is None:
            continue
        known = store.find_by_inn(record["inn"]) or store.find_by_key(record["name_key"])
        if known:
            _enrich(known["id"], record)
        else:
            fresh.append(record)

    if fresh:
        store.save_indexed(fresh)
        for record in fresh:
            _enrich(record["id"], record, with_haystack=True)
    return len(fresh)


def _enrich(supplier_id: str, record: dict, with_haystack: bool = False) -> None:
    found = {field: record[field] for field in LEGAL_FIELDS if record.get(field)}
    if with_haystack:
        found["haystack"] = record["haystack"]
    store.save_enrichment(supplier_id, found)
    saved = store.get(supplier_id)
    if saved:
        score_one(saved)


async def _safe(coroutine):
    try:
        return await coroutine
    except Exception:
        return []


def _from_fns(row: dict) -> dict | None:
    inn = (row.get("inn") or "").strip()
    name = fns.display_name(row)
    okved = (row.get("okved2main") or "").strip()
    kind = fns.kind_of(okved)
    if not inn or not name or not okved or kind == "retail":
        return None

    area = row.get("regionname") or ""
    return _record(
        supplier_id=f"fns:{inn}",
        name=name,
        area=catalog.pretty_area(area),
        region=catalog.region_by_area(area),
        category=fns.category_of(okved),
        kind=kind,
        title=(row.get("okved2mainname") or "")[:60],
        kind_tag=f"okved={okved}",
        source_id="fns",
        source_title="ФНС: Прозрачный бизнес",
        url=fns.CARD_URL.format(token=row.get("token") or ""),
        legal={
            "inn": inn,
            "ogrn": (row.get("ogrn") or "").strip(),
            "okved": okved,
            "okved_name": row.get("okved2mainname") or "",
            "legal_name": row.get("namep") or name,
            "legal_status": row.get("sulst_name_ex") or "",
            "legal_active": 0 if row.get("pr_liq") == "1" else 1,
            "founded": domain.year_of(row.get("dtreg") or ""),
        },
    )


def _from_egrul(row: dict, category: str, kind: str) -> dict | None:
    inn = (row.get("i") or "").strip()
    name = egrul.display_name(row)
    if not inn or len(name) < 3:
        return None

    closed = bool(row.get("e") and row.get("e") != row.get("r"))
    area = catalog.pretty_area((row.get("rn") or "").replace("Г.", "").split("(")[0].strip())
    return _record(
        supplier_id=f"egrul:{inn}",
        name=name,
        area=area,
        region=catalog.region_by_area(area),
        category=category,
        kind=kind,
        title=catalog.title(category),
        kind_tag="egrul",
        source_id="egrul",
        source_title="ЕГРЮЛ (ФНС)",
        url=egrul.CARD_URL.format(query=inn),
        legal={
            "inn": inn,
            "ogrn": (row.get("o") or "").strip(),
            "legal_name": row.get("n") or name,
            "legal_status": "Есть запись о прекращении" if closed else "Действующая организация",
            "legal_active": 0 if closed else 1,
            "manager": egrul.head_of(row.get("g") or ""),
            "founded": domain.year_of(row.get("r") or ""),
        },
    )


def _record(
    *,
    supplier_id: str,
    name: str,
    area: str,
    region: str,
    category: str,
    kind: str,
    title: str,
    kind_tag: str,
    source_id: str,
    source_title: str,
    url: str,
    legal: dict,
) -> dict:
    founded = legal.get("founded")
    record = {
        "id": supplier_id,
        "name": name,
        "name_key": domain.name_key(name),
        "city": "",
        "area": area,
        "region": region,
        "cats": f",{category}," if category else ",wholesale,",
        "cats_titles": [catalog.title(category)] if category else [],
        "kind": title,
        "kind_tag": kind_tag,
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
        "source_title": source_title,
        "sources": [{"id": source_id, "title": source_title, "url": url}],
        "checked_at": time.time(),
        "years": domain.years_text(founded) if founded else "",
        **legal,
    }
    record["haystack"] = " ".join(
        [domain.haystack(record), record.get("okved", ""), record.get("okved_name", ""), area]
    ).lower()[:2000]
    return record
