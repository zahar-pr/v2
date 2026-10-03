import time
from dataclasses import dataclass
from urllib.parse import urlsplit

import catalog
import scoring
from db import (
    JSON_FIELDS,
    NULLABLE_FIELDS,
    NUMERIC_FIELDS,
    _encode,
    _lock,
    connect,
    row_to_dict,
)

INDEXED_FIELDS = (
    "id",
    "name",
    "name_key",
    "city",
    "region",
    "area",
    "cats",
    "kind",
    "kind_tag",
    "kind_class",
    "address",
    "phones",
    "emails",
    "socials",
    "website",
    "hours",
    "wholesale",
    "branches",
    "lat",
    "lon",
    "source",
    "source_title",
    "sources",
    "haystack",
    "distance_km",
    "checked_at",
)


ENRICHED_FIELDS = (
    "about",
    "moq",
    "moq_value",
    "moq_unit",
    "price",
    "price_value",
    "price_unit",
    "price_on_request",
    "delivery",
    "geo",
    "years",
    "founded",
    "inn",
    "ogrn",
    "manager",
    "certs",
    "rating",
    "reviews",
    "emails",
    "phones",
    "website",
    "sources",
    "haystack",
    "price_list",
    "own_delivery",
    "egrul_checked",
    "okved",
    "okved_name",
    "legal_name",
    "legal_status",
    "legal_active",
    "reviews_url",
    "reviews_source",
    "trust_tier",
    "trust_note",
    "clients",
    "products",
    "incident",
)


# «опт» и «упаковка» — не продукт: сравнивать поставщиков надо по одному товару
GENERIC_CATS = frozenset({"wholesale", "packaging"})

SOCIAL_HOSTS = frozenset({"vk.com", "t.me", "instagram.com", "facebook.com", "ok.ru"})

HAS_CONTACTS = "(phones != '[]' OR emails != '[]')"

KIND_ORDER = (
    "CASE kind_class WHEN 'producer' THEN 0 WHEN 'wholesale' THEN 1 "
    "WHEN 'unknown' THEN 2 ELSE 3 END"
)


SCORE_COLUMNS = (
    "score_safety",
    "score_reach",
    "score_volume",
    "score_docs",
    "score_logistics",
    "score_trust",
    "score_reputation",
)


@dataclass(frozen=True)
class Slice:
    """Условие выборки и его параметры — чтобы считать фасеты по срезам."""

    condition: str
    params: list


def priority_sql(weights: dict) -> str:
    if not weights or not any(weights.values()):
        weights = dict(scoring.PRESETS[scoring.DEFAULT_PRESET]["weights"])
    parts = []
    total = 0
    for column in SCORE_COLUMNS:
        weight = max(0, min(100, int(weights.get(column.replace("score_", ""), 0))))
        total += weight
        parts.append(f"{column} * {weight}")
    return f"(({' + '.join(parts)}) / {total or 1}.0)"


# Проверенные поставщики сетей идут первыми при любой сортировке, компании с
# санитарными решениями — последними: это вывод, а не один из факторов балла.
TRUST_ORDER = (
    "CASE WHEN safety_state IN ('banned', 'incident') OR trust_tier = 'blocked' THEN 3 "
    "WHEN safety_state = 'closed' THEN 2 "
    "WHEN trust_tier = 'trusted' THEN 0 ELSE 1 END ASC"
)

# Дешевле — ближе к началу: «ниже рынка», контракт, средний, выше рынка.
PRICE_ORDER = (
    "CASE price_tier WHEN 'low' THEN 0 WHEN 'contract' THEN 1 WHEN 'mid' THEN 2 "
    "WHEN 'high' THEN 3 ELSE 4 END"
)

# «Можно работать»: нет санитарного решения и юрлицо не прекращено.
RISKY = "safety_state NOT IN ('banned', 'incident', 'closed') AND trust_tier != 'blocked'"


def sort_sql(sort: str, weights: dict) -> str:
    priority = priority_sql(weights)
    options = {
        "По приоритету": f"{priority} DESC, name COLLATE NOCASE ASC",
        "Сначала дешёвые": f"{PRICE_ORDER} ASC, {priority} DESC",
        "По полноте данных": f"profile_percent DESC, {priority} DESC",
        "По расстоянию": f"distance_km IS NULL, distance_km ASC, {priority} DESC",
        "По минимальному заказу": f"moq_value IS NULL, moq_value ASC, {priority} DESC",
        "По названию": "name COLLATE NOCASE ASC",
    }
    return f"{TRUST_ORDER}, " + options.get(sort, options["По приоритету"])


def save_indexed(items: list[dict]) -> int:
    if not items:
        return 0
    now = time.time()
    columns = ", ".join(INDEXED_FIELDS)
    holders = ", ".join("?" for _ in INDEXED_FIELDS)
    updates = ", ".join(
        f"{field}=excluded.{field}" for field in INDEXED_FIELDS if field not in ("id", "haystack")
    )
    sql = (
        f"INSERT INTO suppliers ({columns}, created_at, updated_at) "
        f"VALUES ({holders}, ?, ?) "
        f"ON CONFLICT(id) DO UPDATE SET {updates}, updated_at=excluded.updated_at, "
        "haystack=excluded.haystack || ' ' || suppliers.about || ' ' || suppliers.certs"
    )
    rows = []
    for item in items:
        values = []
        for field in INDEXED_FIELDS:
            value = item.get(field)
            if value is None:
                if field in JSON_FIELDS:
                    value = []
                elif field in NULLABLE_FIELDS:
                    value = None
                elif field in NUMERIC_FIELDS:
                    value = 0
                else:
                    value = ""
            values.append(_encode(value))
        rows.append((*values, now, now))
    with _lock:
        connection = connect()
        connection.executemany(sql, rows)
        connection.commit()
    return len(rows)


def prune_city(city: str, seen_after: float) -> int:
    with _lock:
        connection = connect()
        cursor = connection.execute(
            "DELETE FROM suppliers WHERE city=? AND id LIKE 'osm:%' AND checked_at < ?",
            (city, seen_after),
        )
        connection.commit()
    return cursor.rowcount


def save_enrichment(supplier_id: str, data: dict) -> None:
    fields = [field for field in ENRICHED_FIELDS if field in data]
    assignments = ", ".join(f"{field}=?" for field in fields)
    values = [_encode(data[field]) for field in fields]
    with _lock:
        connection = connect()
        connection.execute(
            f"UPDATE suppliers SET {assignments}, enriched_at=?, enrich_tries=enrich_tries+1, "
            "updated_at=? WHERE id=?",
            (*values, time.time(), time.time(), supplier_id),
        )
        connection.commit()


def mark_enrich_failed(supplier_id: str) -> None:
    with _lock:
        connection = connect()
        connection.execute(
            "UPDATE suppliers SET enrich_tries=enrich_tries+1 WHERE id=?", (supplier_id,)
        )
        connection.commit()


def set_verified(supplier_id: str, verified: bool, by: str) -> bool:
    with _lock:
        connection = connect()
        cursor = connection.execute(
            "UPDATE suppliers SET verified=?, verified_by=?, updated_at=? WHERE id=?",
            (1 if verified else 0, by, time.time(), supplier_id),
        )
        connection.commit()
    return cursor.rowcount > 0


def get(supplier_id: str) -> dict | None:
    connection = connect()
    row = connection.execute("SELECT * FROM suppliers WHERE id=?", (supplier_id,)).fetchone()
    return row_to_dict(row) if row else None


def get_many(ids: list[str]) -> list[dict]:
    if not ids:
        return []
    holders = ", ".join("?" for _ in ids)
    connection = connect()
    rows = connection.execute(
        f"SELECT * FROM suppliers WHERE id IN ({holders})", tuple(ids)
    ).fetchall()
    found = {row["id"]: row_to_dict(row) for row in rows}
    return [found[key] for key in ids if key in found]


def search(
    query: str = "",
    category: str = "",
    region: str = "",
    city: str = "",
    only_docs: bool = False,
    only_verified: bool = False,
    only_contacts: bool = False,
    only_safe: bool = False,
    price: str = "",
    delivers: bool = True,
    kinds: tuple[str, ...] = (),
    status: str = "",
    weights: dict | None = None,
    sort: str = "По приоритету",
    page: int = 1,
    per_page: int = 12,
) -> tuple[list[dict], int, dict]:
    base, base_values = _conditions(
        query,
        region,
        city,
        only_docs,
        only_verified,
        only_contacts,
        only_safe,
        price,
        delivers,
        status,
    )
    by_cat, cat_values = _category_clause(category)
    by_kind, kind_values = _kind_clause(kinds)

    where = [*base, *by_cat, *by_kind]
    params = [*base_values, *cat_values, *kind_values]
    condition = " AND ".join(where)
    connection = connect()
    total = connection.execute(
        f"SELECT COUNT(*) FROM suppliers WHERE {condition}", tuple(params)
    ).fetchone()[0]
    rows = connection.execute(
        f"SELECT * FROM suppliers WHERE {condition} "
        f"ORDER BY {sort_sql(sort, weights or {})} LIMIT ? OFFSET ?",
        (*params, per_page, max(0, (page - 1) * per_page)),
    ).fetchall()
    facets = _facets(
        Slice(condition, params),
        Slice(" AND ".join([*base, *by_cat]), [*base_values, *cat_values]),
        Slice(" AND ".join([*base, *by_kind]), [*base_values, *kind_values]),
    )
    return [row_to_dict(row) for row in rows], total, facets


def _category_clause(category: str) -> tuple[list[str], list]:
    chosen = [item for item in (category or "").split(",") if item]
    if not chosen:
        return [], []
    return ["(" + " OR ".join("cats LIKE ?" for _ in chosen) + ")"], [
        f"%,{item},%" for item in chosen
    ]


def _kind_clause(kinds: tuple[str, ...]) -> tuple[list[str], list]:
    if not kinds:
        return [], []
    return ["kind_class IN (" + ", ".join("?" for _ in kinds) + ")"], list(kinds)


def _conditions(
    query: str,
    region: str,
    city: str,
    only_docs: bool,
    only_verified: bool,
    only_contacts: bool,
    only_safe: bool,
    price: str,
    delivers: bool,
    status: str,
) -> tuple[list[str], list]:
    where, params = ["1=1"], []

    if city:
        clause, values = _place_clause("city", city, catalog.region_of(city), delivers)
        where.append(clause)
        params += values
    elif region:
        clause, values = _place_clause("region", region, region, delivers)
        where.append(clause)
        params += values
    if only_safe:
        where.append(RISKY)
    if price:
        where.append("price_tier = ?")
        params.append(price)
    if only_docs:
        where.append("certs != '[]'")
    if only_verified:
        where.append("verified = 1")
    if only_contacts:
        where.append(HAS_CONTACTS)
    if status:
        where.append("id IN (SELECT supplier_id FROM pipeline WHERE status = ?)")
        params.append(status)
    for word in query.lower().split():
        where.append("haystack LIKE ?")
        params.append(f"%{word}%")
    return where, params


def _place_clause(
    column: str, value: str, region: str, delivers: bool
) -> tuple[str, list]:
    """Закупщика интересует не прописка поставщика, а куда он возит.

    Поэтому к местным добавляются те, кто сам заявил поставки по всей России или
    по этому региону: иначе федеральный поставщик выпадает из выдачи по городу.
    """
    if not delivers:
        return f"{column} = ?", [value]
    if not region:
        return f"({column} = ? OR delivers_all = 1)", [value]
    return (
        f"({column} = ? OR delivers_all = 1 OR delivery_regions LIKE ?)",
        [value, f"%,{region},%"],
    )


def _facets(current: Slice, without_kinds: Slice, without_cats: Slice) -> dict:
    connection = connect()
    types = {
        row["kind_class"]: row["n"]
        for row in connection.execute(
            f"SELECT kind_class, COUNT(*) AS n FROM suppliers WHERE {without_kinds.condition} "
            "GROUP BY kind_class",
            tuple(without_kinds.params),
        )
    }
    sums = ", ".join(
        f"SUM(CASE WHEN cats LIKE '%,{item.id},%' THEN 1 ELSE 0 END) AS {item.id}"
        for item in catalog.CATEGORIES
    )
    cats = connection.execute(
        f"SELECT {sums} FROM suppliers WHERE {without_cats.condition}",
        tuple(without_cats.params),
    ).fetchone()
    counters = connection.execute(
        f"SELECT SUM(CASE WHEN {HAS_CONTACTS} THEN 1 ELSE 0 END) AS contacts, "
        "SUM(CASE WHEN certs != '[]' THEN 1 ELSE 0 END) AS docs, "
        "SUM(CASE WHEN verified = 1 THEN 1 ELSE 0 END) AS verified, "
        f"SUM(CASE WHEN {RISKY} THEN 0 ELSE 1 END) AS risky, "
        "SUM(CASE WHEN price_tier = 'low' THEN 1 ELSE 0 END) AS price_low, "
        "SUM(CASE WHEN price_tier = 'mid' THEN 1 ELSE 0 END) AS price_mid, "
        "SUM(CASE WHEN price_tier = 'high' THEN 1 ELSE 0 END) AS price_high, "
        "SUM(CASE WHEN price_tier = 'contract' THEN 1 ELSE 0 END) AS price_contract, "
        "AVG(profile_percent) AS fullness "
        f"FROM suppliers WHERE {current.condition}",
        tuple(current.params),
    ).fetchone()
    return {
        "types": types,
        "cats": {item.id: cats[item.id] or 0 for item in catalog.CATEGORIES},
        "withContacts": counters["contacts"] or 0,
        "withDocs": counters["docs"] or 0,
        "verified": counters["verified"] or 0,
        "risky": counters["risky"] or 0,
        "prices": {
            "low": counters["price_low"] or 0,
            "mid": counters["price_mid"] or 0,
            "high": counters["price_high"] or 0,
            "contract": counters["price_contract"] or 0,
        },
        "fullness": round(counters["fullness"] or 0),
    }


def save_scores(supplier_id: str, scores: dict) -> None:
    """Балл по факторам плюс выводы, по которым потом идут фильтры и сортировки."""
    with _lock:
        connection = connect()
        connection.execute(
            "UPDATE suppliers SET score_reach=?, score_volume=?, score_docs=?, "
            "score_logistics=?, score_trust=?, score_reputation=?, score_safety=?, "
            "safety_state=?, price_tier=?, profile_percent=?, delivers_all=?, "
            "delivery_regions=?, score=?, scored_at=?, "
            "rating=CASE WHEN reviews IS NULL THEN ? ELSE rating END WHERE id=?",
            (
                scores["reach"],
                scores["volume"],
                scores["docs"],
                scores["logistics"],
                scores["trust"],
                scores["reputation"],
                scores["safety"],
                scores.get("safety_state", ""),
                scores.get("price_tier", ""),
                scores.get("profile_percent", 0),
                1 if scores.get("delivers_all") else 0,
                scores.get("delivery_regions", ""),
                scores["total"],
                time.time(),
                round(scores["total"] / 20, 1),
                supplier_id,
            ),
        )
        connection.commit()


def unscored(limit: int = 1000) -> list[dict]:
    connection = connect()
    rows = connection.execute(
        "SELECT * FROM suppliers WHERE scored_at = 0 LIMIT ?", (limit,)
    ).fetchall()
    return [row_to_dict(row) for row in rows]


def save_kind(supplier_id: str, kind_class: str, cats: str) -> None:
    with _lock:
        connection = connect()
        if cats:
            connection.execute(
                "UPDATE suppliers SET kind_class=?, cats=?, wholesale=? WHERE id=?",
                (
                    kind_class,
                    cats,
                    1 if kind_class in ("producer", "wholesale") else 0,
                    supplier_id,
                ),
            )
        else:
            connection.execute(
                "UPDATE suppliers SET kind_class=?, wholesale=? WHERE id=?",
                (kind_class, 1 if kind_class in ("producer", "wholesale") else 0, supplier_id),
            )
        connection.commit()


def find_by_key(name_key: str) -> dict | None:
    connection = connect()
    row = connection.execute(
        "SELECT * FROM suppliers WHERE name_key=? ORDER BY score DESC LIMIT 1", (name_key,)
    ).fetchone()
    return row_to_dict(row) if row else None


def find_by_inn(inn: str) -> dict | None:
    connection = connect()
    row = connection.execute("SELECT * FROM suppliers WHERE inn=? LIMIT 1", (inn,)).fetchone()
    return row_to_dict(row) if row else None


def pending_enrichment(limit: int, max_tries: int = 3) -> list[dict]:
    connection = connect()
    rows = connection.execute(
        "SELECT * FROM suppliers WHERE website != '' AND enriched_at = 0 AND enrich_tries < ? "
        "ORDER BY enrich_tries ASC, " + KIND_ORDER + ", score DESC LIMIT ?",
        (max_tries, limit),
    ).fetchall()
    return [row_to_dict(row) for row in rows]


def pending_reviews(limit: int, recheck_after: float = 30 * 24 * 3600) -> list[dict]:
    connection = connect()
    rows = connection.execute(
        "SELECT * FROM suppliers WHERE kind_class != 'retail' "
        "AND (reviews_checked = 0 OR (reviews_source = '' AND reviews_checked < ?)) "
        "ORDER BY reviews_checked ASC, " + KIND_ORDER + ", score DESC LIMIT ?",
        (time.time() - recheck_after, limit),
    ).fetchall()
    return [row_to_dict(row) for row in rows]


def mark_reviews_checked(supplier_id: str) -> None:
    with _lock:
        connection = connect()
        connection.execute(
            "UPDATE suppliers SET reviews_checked=? WHERE id=?", (time.time(), supplier_id)
        )
        connection.commit()


def pending_fns(limit: int) -> list[dict]:
    connection = connect()
    rows = connection.execute(
        "SELECT * FROM suppliers WHERE fns_checked = 0 AND kind_class != 'retail' "
        "ORDER BY " + KIND_ORDER + ", score DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [row_to_dict(row) for row in rows]


def mark_fns_checked(supplier_id: str) -> None:
    with _lock:
        connection = connect()
        connection.execute(
            "UPDATE suppliers SET fns_checked=? WHERE id=?", (time.time(), supplier_id)
        )
        connection.commit()


def pending_egrul(limit: int) -> list[dict]:
    connection = connect()
    rows = connection.execute(
        "SELECT * FROM suppliers WHERE egrul_checked = 0 AND manager = '' "
        "AND (inn != '' OR wholesale = 1) "
        "ORDER BY " + KIND_ORDER + ", score_reach DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [row_to_dict(row) for row in rows]


def mark_egrul_checked(supplier_id: str) -> None:
    with _lock:
        connection = connect()
        connection.execute(
            "UPDATE suppliers SET egrul_checked=? WHERE id=?", (time.time(), supplier_id)
        )
        connection.commit()


def save_center(city: str, lat: float, lon: float) -> None:
    with _lock:
        connection = connect()
        connection.execute(
            "INSERT INTO centers (city, lat, lon) VALUES (?, ?, ?) "
            "ON CONFLICT(city) DO UPDATE SET lat=excluded.lat, lon=excluded.lon",
            (city, lat, lon),
        )
        connection.commit()


def center_of(city: str) -> tuple[float, float] | None:
    connection = connect()
    row = connection.execute("SELECT lat, lon FROM centers WHERE city=?", (city,)).fetchone()
    return (row["lat"], row["lon"]) if row else None


def save_distances(city: str, center: tuple[float, float]) -> int:
    lat, lon = center
    with _lock:
        connection = connect()
        cursor = connection.execute(
            "UPDATE suppliers SET distance_km = ROUND("
            "111.0 * SQRT((lat - ?) * (lat - ?) + (lon - ?) * (lon - ?) * 0.33), 1) "
            "WHERE city = ? AND lat IS NOT NULL AND lon IS NOT NULL",
            (lat, lat, lon, lon, city),
        )
        connection.commit()
    return cursor.rowcount


def refreshed_at(city: str) -> float:
    connection = connect()
    row = connection.execute("SELECT refreshed_at FROM refreshes WHERE city=?", (city,)).fetchone()
    return row["refreshed_at"] if row else 0.0


def refresh_row(city: str) -> dict | None:
    connection = connect()
    row = connection.execute("SELECT * FROM refreshes WHERE city=?", (city,)).fetchone()
    return dict(row) if row else None


def forget_city(city: str) -> None:
    with _lock:
        connection = connect()
        connection.execute("DELETE FROM refreshes WHERE city=?", (city,))
        connection.commit()


def mark_refreshed(city: str, found: int, note: str = "") -> None:
    with _lock:
        connection = connect()
        connection.execute(
            "INSERT INTO refreshes (city, refreshed_at, found, note) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(city) DO UPDATE SET refreshed_at=excluded.refreshed_at, "
            "found=excluded.found, note=excluded.note",
            (city, time.time(), found, note),
        )
        connection.commit()


def count_for(**filters) -> int:
    _, total, _ = search(per_page=1, **filters)
    return total


def relax_options(filters: dict, labels: dict) -> list[dict]:
    active = [key for key in labels if _is_active(filters, key)]
    singles = []
    for key in active:
        found = count_for(**_without(filters, [key]))
        if found:
            singles.append({"key": key, "keys": [key], "title": labels[key], "count": found})
    if singles:
        return sorted(singles, key=lambda item: -item["count"])[:4]

    pairs = []
    for first in range(len(active)):
        for second in range(first + 1, len(active)):
            keys = [active[first], active[second]]
            found = count_for(**_without(filters, keys))
            if found:
                title = f"{labels[keys[0]]} и {labels[keys[1]].lower()}"
                pairs.append({"key": "+".join(keys), "keys": keys, "title": title, "count": found})
    return sorted(pairs, key=lambda item: -item["count"])[:3]


def _is_active(filters: dict, key: str) -> bool:
    value = filters.get(key)
    if key == "kinds":
        return bool(value)
    return bool(value)


def _without(filters: dict, keys: list[str]) -> dict:
    relaxed = dict(filters)
    for key in keys:
        if key == "kinds":
            relaxed["kinds"] = ()
        elif key in ("only_docs", "only_verified", "only_contacts", "only_safe"):
            relaxed[key] = False
        elif key == "delivers":
            relaxed[key] = True
        else:
            relaxed[key] = ""
    return relaxed


# Чем больше строк таблицы сравнения окажется непустыми, тем полезнее пара поставщиков.
# Коммерческие условия и отзывы встречаются реже прочего, поэтому весят больше.
COMPARE_FIELDS = (
    ("moq", 2),
    ("price", 2),
    ("delivery", 2),
    ("geo", 2),
    ("about", 1),
    ("address", 1),
    ("hours", 1),
    ("website", 1),
    ("years", 1),
    ("inn", 1),
    ("ogrn", 1),
    ("legal_name", 1),
    ("legal_status", 1),
    ("okved_name", 1),
    ("manager", 1),
)
FULLNESS = " + ".join(
    (
        *(f"(IFNULL({field}, '') != '') * {weight}" for field, weight in COMPARE_FIELDS),
        "(phones != '[]')",
        "(emails != '[]')",
        "(certs != '[]') * 2",
        "(socials != '[]')",
        "(verified = 1)",
        "(IFNULL(reviews_source, '') != '') * 3",
        "(comments_count > 0) * 3",
    )
)


# Пара, с которой открывается «Сравнить»: один город, один продукт, у обоих реквизиты,
# руководитель и телефон — видно, что сравниваются все строки. Если кого-то из них нет
# в индексе, берём самую заполненную пару одного продукта, какую найдём.
PINNED = ("хлебозавод2", "донскиепекарни")


def showcase(size: int = 2) -> list[str]:
    """Пара поставщиков одного продукта с самыми заполненными полями — пример сравнения."""
    pinned = _pinned()
    if len(pinned) == len(PINNED):
        return pinned

    rows = (
        connect()
        .execute(
            f"SELECT id, city, region, cats, website, inn, {FULLNESS} AS filled FROM suppliers "
            f"WHERE kind_class != 'retail' AND {HAS_CONTACTS} ORDER BY filled DESC LIMIT 300"
        )
        .fetchall()
    )

    by_cat: dict[str, list] = {}
    for row in rows:
        for item in (row["cats"] or "").split(","):
            if item and item not in GENERIC_CATS:
                by_cat.setdefault(item, []).append(row)

    best, best_weight = [], -1
    for found in by_cat.values():
        picked = _distinct(found, size)
        if len(picked) < size:
            continue
        weight = sum(row["filled"] for row in picked) + _closeness(picked)
        if weight > best_weight:
            best, best_weight = picked, weight
    return [row["id"] for row in best or _distinct(rows, size)]


def _pinned() -> list[str]:
    holders = ", ".join("?" for _ in PINNED)
    found = {
        row["name_key"]: row["id"]
        for row in connect().execute(
            f"SELECT id, name_key FROM suppliers WHERE name_key IN ({holders})", PINNED
        )
    }
    return [found[key] for key in PINNED if key in found]


def _closeness(rows: list) -> int:
    """Поставщиков одного города сравнивать нагляднее, одного региона — тоже."""
    if len({row["city"] for row in rows}) == 1:
        return 3
    return 1 if len({row["region"] for row in rows}) == 1 else 0


def _distinct(rows: list, size: int) -> list:
    """Одну и ту же компанию в сравнение не берём: сайт и ИНН должны различаться."""
    taken, seen = [], set()
    for row in rows:
        marks = {mark for mark in (_host(row["website"]), row["inn"]) if mark}
        if marks & seen:
            continue
        seen |= marks
        taken.append(row)
        if len(taken) == size:
            break
    return taken


def _host(website: str | None) -> str:
    host = urlsplit(website or "").netloc.lower().removeprefix("www.")
    return "" if host in SOCIAL_HOSTS else host


def best_defaults() -> dict:
    connection = connect()
    alive = "(phones != '[]' OR emails != '[]' OR comments_count > 0 OR reviews_source != '')"
    region = connection.execute(
        f"SELECT region, COUNT(*) AS total, SUM(CASE WHEN {alive} THEN 1 ELSE 0 END) AS alive "
        "FROM suppliers WHERE kind_class != 'retail' AND region != '' "
        "GROUP BY region ORDER BY alive * 6 + total DESC LIMIT 1"
    ).fetchone()
    best_region = region["region"] if region else ""

    rows = connection.execute(
        f"SELECT cats, COUNT(*) AS total, SUM(CASE WHEN {alive} THEN 1 ELSE 0 END) AS alive "
        "FROM suppliers WHERE kind_class != 'retail' AND region = ? GROUP BY cats",
        (best_region,),
    ).fetchall()

    counts: dict[str, int] = {}
    for row in rows:
        weight = (row["alive"] or 0) * 6 + row["total"]
        for item in (row["cats"] or "").split(","):
            if item:
                counts[item] = counts.get(item, 0) + weight
    return {
        "region": best_region,
        "category": max(counts, key=counts.get) if counts else "",
    }


def stats() -> dict:
    connection = connect()
    row = connection.execute(
        "SELECT COUNT(*) AS total, "
        "SUM(CASE WHEN certs != '[]' THEN 1 ELSE 0 END) AS with_docs, "
        "SUM(CASE WHEN verified = 1 THEN 1 ELSE 0 END) AS verified, "
        "SUM(CASE WHEN enriched_at > 0 THEN 1 ELSE 0 END) AS enriched, "
        "SUM(CASE WHEN legal_name != '' THEN 1 ELSE 0 END) AS with_legal, "
        "SUM(CASE WHEN reviews IS NOT NULL OR rating IS NOT NULL AND reviews_source != '' "
        "THEN 1 ELSE 0 END) AS with_reviews, "
        "SUM(CASE WHEN phones != '[]' THEN 1 ELSE 0 END) AS with_phone, "
        "SUM(CASE WHEN kind_class = 'producer' THEN 1 ELSE 0 END) AS producers, "
        "SUM(CASE WHEN kind_class = 'wholesale' THEN 1 ELSE 0 END) AS wholesale, "
        "SUM(CASE WHEN kind_class = 'retail' THEN 1 ELSE 0 END) AS retail "
        "FROM suppliers"
    ).fetchone()
    cities = connection.execute("SELECT COUNT(*) FROM refreshes WHERE found > 0").fetchone()[0]
    return {
        "total": row["total"] or 0,
        "withDocs": row["with_docs"] or 0,
        "verified": row["verified"] or 0,
        "enriched": row["enriched"] or 0,
        "withLegal": row["with_legal"] or 0,
        "withReviews": row["with_reviews"] or 0,
        "withPhone": row["with_phone"] or 0,
        "producers": row["producers"] or 0,
        "wholesale": row["wholesale"] or 0,
        "retail": row["retail"] or 0,
        "citiesIndexed": cities or 0,
    }
