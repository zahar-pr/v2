import json
import os
import sqlite3
import threading
import time

DB_PATH = os.environ.get(
    "DB_PATH",
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "provizia.db"
    ),
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS suppliers (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    name_key TEXT NOT NULL,
    city TEXT NOT NULL,
    region TEXT NOT NULL,
    cats TEXT NOT NULL DEFAULT '',
    kind TEXT NOT NULL DEFAULT '',
    kind_tag TEXT NOT NULL DEFAULT '',
    kind_class TEXT NOT NULL DEFAULT 'unknown',
    address TEXT NOT NULL DEFAULT '',
    phones TEXT NOT NULL DEFAULT '[]',
    emails TEXT NOT NULL DEFAULT '[]',
    socials TEXT NOT NULL DEFAULT '[]',
    website TEXT NOT NULL DEFAULT '',
    hours TEXT NOT NULL DEFAULT '',
    wholesale INTEGER NOT NULL DEFAULT 0,
    branches INTEGER NOT NULL DEFAULT 1,
    lat REAL,
    lon REAL,
    source TEXT NOT NULL DEFAULT '',
    source_title TEXT NOT NULL DEFAULT '',
    sources TEXT NOT NULL DEFAULT '[]',
    about TEXT NOT NULL DEFAULT '',
    moq TEXT NOT NULL DEFAULT '',
    moq_value REAL,
    moq_unit TEXT NOT NULL DEFAULT '',
    price TEXT NOT NULL DEFAULT '',
    price_value REAL,
    price_unit TEXT NOT NULL DEFAULT '',
    price_on_request INTEGER NOT NULL DEFAULT 0,
    delivery TEXT NOT NULL DEFAULT '',
    geo TEXT NOT NULL DEFAULT '',
    years TEXT NOT NULL DEFAULT '',
    founded INTEGER,
    inn TEXT NOT NULL DEFAULT '',
    ogrn TEXT NOT NULL DEFAULT '',
    manager TEXT NOT NULL DEFAULT '',
    certs TEXT NOT NULL DEFAULT '[]',
    rating REAL,
    reviews INTEGER,
    verified INTEGER NOT NULL DEFAULT 0,
    verified_by TEXT NOT NULL DEFAULT '',
    score INTEGER NOT NULL DEFAULT 0,
    level TEXT NOT NULL DEFAULT 'low',
    verdict TEXT NOT NULL DEFAULT '',
    plus TEXT NOT NULL DEFAULT '[]',
    minus TEXT NOT NULL DEFAULT '[]',
    haystack TEXT NOT NULL DEFAULT '',
    score_reach INTEGER NOT NULL DEFAULT 0,
    score_volume INTEGER NOT NULL DEFAULT 0,
    score_docs INTEGER NOT NULL DEFAULT 0,
    score_logistics INTEGER NOT NULL DEFAULT 0,
    score_trust INTEGER NOT NULL DEFAULT 0,
    scored_at REAL NOT NULL DEFAULT 0,
    distance_km REAL,
    price_list TEXT NOT NULL DEFAULT '',
    own_delivery INTEGER NOT NULL DEFAULT 0,
    egrul_name TEXT NOT NULL DEFAULT '',
    egrul_head TEXT NOT NULL DEFAULT '',
    egrul_registered TEXT NOT NULL DEFAULT '',
    egrul_closed INTEGER NOT NULL DEFAULT 0,
    egrul_checked REAL NOT NULL DEFAULT 0,
    checked_at REAL NOT NULL DEFAULT 0,
    enriched_at REAL NOT NULL DEFAULT 0,
    enrich_tries INTEGER NOT NULL DEFAULT 0,
    created_at REAL NOT NULL DEFAULT 0,
    updated_at REAL NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS suppliers_city ON suppliers(city);
CREATE INDEX IF NOT EXISTS suppliers_region ON suppliers(region);
CREATE INDEX IF NOT EXISTS suppliers_score ON suppliers(score DESC);
CREATE INDEX IF NOT EXISTS suppliers_enrich ON suppliers(enriched_at, enrich_tries);

CREATE TABLE IF NOT EXISTS notes (
    user_id TEXT NOT NULL,
    supplier_id TEXT NOT NULL,
    text TEXT NOT NULL DEFAULT '',
    updated_at REAL NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, supplier_id)
);

CREATE TABLE IF NOT EXISTS centers (
    city TEXT PRIMARY KEY,
    lat REAL NOT NULL,
    lon REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS pipeline (
    user_id TEXT NOT NULL,
    supplier_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'new',
    updated_at REAL NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, supplier_id)
);

CREATE TABLE IF NOT EXISTS refreshes (
    city TEXT PRIMARY KEY,
    refreshed_at REAL NOT NULL DEFAULT 0,
    found INTEGER NOT NULL DEFAULT 0,
    note TEXT NOT NULL DEFAULT ''
);
"""

JSON_FIELDS = ("phones", "emails", "certs", "plus", "minus", "sources", "socials")

INDEXED_FIELDS = (
    "id",
    "name",
    "name_key",
    "city",
    "region",
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
    "egrul_name",
    "egrul_head",
    "egrul_registered",
    "egrul_closed",
    "egrul_checked",
)

KIND_ORDER = (
    "CASE kind_class WHEN 'producer' THEN 0 WHEN 'wholesale' THEN 1 "
    "WHEN 'unknown' THEN 2 ELSE 3 END"
)

SCORE_COLUMNS = (
    "score_reach",
    "score_volume",
    "score_docs",
    "score_logistics",
    "score_trust",
)


def priority_sql(weights: dict) -> str:
    parts = []
    total = 0
    for column in SCORE_COLUMNS:
        weight = max(0, min(100, int(weights.get(column.replace("score_", ""), 0))))
        total += weight
        parts.append(f"{column} * {weight}")
    return f"(({' + '.join(parts)}) / {total or 1}.0)"


def sort_sql(sort: str, weights: dict) -> str:
    priority = priority_sql(weights)
    options = {
        "По приоритету": f"{priority} DESC, name COLLATE NOCASE ASC",
        "По расстоянию": f"distance_km IS NULL, distance_km ASC, {priority} DESC",
        "По минимальному заказу": f"moq_value IS NULL, moq_value ASC, {priority} DESC",
        "По названию": "name COLLATE NOCASE ASC",
    }
    return options.get(sort, options["По приоритету"])


_lock = threading.Lock()
_connection: sqlite3.Connection | None = None


ADDED_COLUMNS = (
    ("socials", "TEXT NOT NULL DEFAULT '[]'"),
    ("kind_tag", "TEXT NOT NULL DEFAULT ''"),
    ("kind_class", "TEXT NOT NULL DEFAULT 'unknown'"),
    ("score_reach", "INTEGER NOT NULL DEFAULT 0"),
    ("score_volume", "INTEGER NOT NULL DEFAULT 0"),
    ("score_docs", "INTEGER NOT NULL DEFAULT 0"),
    ("score_logistics", "INTEGER NOT NULL DEFAULT 0"),
    ("score_trust", "INTEGER NOT NULL DEFAULT 0"),
    ("scored_at", "REAL NOT NULL DEFAULT 0"),
    ("distance_km", "REAL"),
    ("price_list", "TEXT NOT NULL DEFAULT ''"),
    ("own_delivery", "INTEGER NOT NULL DEFAULT 0"),
    ("egrul_name", "TEXT NOT NULL DEFAULT ''"),
    ("egrul_head", "TEXT NOT NULL DEFAULT ''"),
    ("egrul_registered", "TEXT NOT NULL DEFAULT ''"),
    ("egrul_closed", "INTEGER NOT NULL DEFAULT 0"),
    ("egrul_checked", "REAL NOT NULL DEFAULT 0"),
)


def connect() -> sqlite3.Connection:
    global _connection
    if _connection is None:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        _connection = sqlite3.connect(DB_PATH, check_same_thread=False)
        _connection.row_factory = sqlite3.Row
        _connection.execute("PRAGMA journal_mode=WAL")
        _connection.execute("PRAGMA synchronous=NORMAL")
        _connection.executescript(SCHEMA)
        _migrate(_connection)
        _connection.commit()
    return _connection


def _migrate(connection: sqlite3.Connection) -> None:
    known = {row["name"] for row in connection.execute("PRAGMA table_info(suppliers)")}
    for column, definition in ADDED_COLUMNS:
        if column not in known:
            connection.execute(f"ALTER TABLE suppliers ADD COLUMN {column} {definition}")


def row_to_dict(row: sqlite3.Row) -> dict:
    item = dict(row)
    for field in JSON_FIELDS:
        if field in item:
            item[field] = json.loads(item[field] or "[]")
    return item


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
            if value is None and field in JSON_FIELDS:
                value = []
            values.append(_encode(value))
        rows.append((*values, now, now))
    with _lock:
        connection = connect()
        connection.executemany(sql, rows)
        connection.commit()
    return len(rows)


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


def save_rating(supplier_id: str, score: int, level: str, verdict: str, plus, minus) -> None:
    with _lock:
        connection = connect()
        connection.execute(
            "UPDATE suppliers SET score=?, level=?, verdict=?, plus=?, minus=?, "
            "rating=CASE WHEN reviews IS NULL THEN ? ELSE rating END WHERE id=?",
            (
                score,
                level,
                verdict,
                json.dumps(plus, ensure_ascii=False),
                json.dumps(minus, ensure_ascii=False),
                round(score / 20, 1),
                supplier_id,
            ),
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
    only_wholesale: bool = False,
    only_contacts: bool = False,
    kinds: tuple[str, ...] = (),
    status: str = "",
    user_id: str = "",
    weights: dict | None = None,
    sort: str = "По приоритету",
    page: int = 1,
    per_page: int = 12,
) -> tuple[list[dict], int, dict]:
    weights = weights or {}
    where = ["1=1"]
    params: list = []

    if category:
        where.append("cats LIKE ?")
        params.append(f"%,{category},%")
    if city:
        where.append("city = ?")
        params.append(city)
    elif region:
        where.append("region = ?")
        params.append(region)
    if only_docs:
        where.append("certs != '[]'")
    if only_verified:
        where.append("verified = 1")
    if only_wholesale:
        where.append("wholesale = 1")
    if only_contacts:
        where.append("(phones != '[]' OR emails != '[]')")
    if status and user_id:
        where.append("id IN (SELECT supplier_id FROM pipeline WHERE user_id = ? AND status = ?)")
        params.extend([user_id, status])
    for word in query.lower().split():
        where.append("haystack LIKE ?")
        params.append(f"%{word}%")

    base_where = list(where)
    base_params = list(params)
    if kinds:
        holders = ", ".join("?" for _ in kinds)
        where.append(f"kind_class IN ({holders})")
        params.extend(kinds)

    condition = " AND ".join(where)
    order = sort_sql(sort, weights)
    offset = max(0, (page - 1) * per_page)

    connection = connect()
    total = connection.execute(
        f"SELECT COUNT(*) FROM suppliers WHERE {condition}", tuple(params)
    ).fetchone()[0]
    rows = connection.execute(
        f"SELECT * FROM suppliers WHERE {condition} ORDER BY {order} LIMIT ? OFFSET ?",
        (*params, per_page, offset),
    ).fetchall()

    wide = " AND ".join(base_where)
    types = {
        row["kind_class"]: row["n"]
        for row in connection.execute(
            f"SELECT kind_class, COUNT(*) AS n FROM suppliers WHERE {wide} GROUP BY kind_class",
            tuple(base_params),
        )
    }
    counters = connection.execute(
        f"SELECT SUM(CASE WHEN phones != '[]' OR emails != '[]' THEN 1 ELSE 0 END) AS contacts, "
        f"SUM(CASE WHEN certs != '[]' THEN 1 ELSE 0 END) AS docs, "
        f"SUM(CASE WHEN verified = 1 THEN 1 ELSE 0 END) AS verified "
        f"FROM suppliers WHERE {condition}",
        tuple(params),
    ).fetchone()

    found = {
        "types": types,
        "withContacts": counters["contacts"] or 0,
        "withDocs": counters["docs"] or 0,
        "verified": counters["verified"] or 0,
    }
    return [row_to_dict(row) for row in rows], total, found


def save_scores(supplier_id: str, scores: dict) -> None:
    with _lock:
        connection = connect()
        connection.execute(
            "UPDATE suppliers SET score_reach=?, score_volume=?, score_docs=?, "
            "score_logistics=?, score_trust=?, score=?, scored_at=?, "
            "rating=CASE WHEN reviews IS NULL THEN ? ELSE rating END WHERE id=?",
            (
                scores["reach"],
                scores["volume"],
                scores["docs"],
                scores["logistics"],
                scores["trust"],
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


def statuses_of(user_id: str) -> dict:
    connection = connect()
    rows = connection.execute(
        "SELECT supplier_id, status FROM pipeline WHERE user_id=?", (user_id,)
    ).fetchall()
    return {row["supplier_id"]: row["status"] for row in rows}


def set_status(user_id: str, supplier_id: str, status: str) -> dict:
    now = time.time()
    with _lock:
        connection = connect()
        if status in ("", "new"):
            connection.execute(
                "DELETE FROM pipeline WHERE user_id=? AND supplier_id=?",
                (user_id, supplier_id),
            )
        else:
            connection.execute(
                "INSERT INTO pipeline (user_id, supplier_id, status, updated_at) "
                "VALUES (?, ?, ?, ?) ON CONFLICT(user_id, supplier_id) DO UPDATE SET "
                "status=excluded.status, updated_at=excluded.updated_at",
                (user_id, supplier_id, status, now),
            )
        connection.commit()
    return {"supplier_id": supplier_id, "status": status or "new", "updated_at": now}


def status_counts(user_id: str) -> dict:
    connection = connect()
    rows = connection.execute(
        "SELECT status, COUNT(*) AS n FROM pipeline WHERE user_id=? GROUP BY status",
        (user_id,),
    ).fetchall()
    return {row["status"]: row["n"] for row in rows}


def pending_egrul(limit: int) -> list[dict]:
    connection = connect()
    rows = connection.execute(
        "SELECT * FROM suppliers WHERE egrul_checked = 0 AND (inn != '' OR wholesale = 1) "
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


def pending_enrichment(limit: int, max_tries: int = 3) -> list[dict]:
    connection = connect()
    rows = connection.execute(
        "SELECT * FROM suppliers WHERE website != '' AND enriched_at = 0 AND enrich_tries < ? "
        "ORDER BY enrich_tries ASC, " + KIND_ORDER + ", score DESC LIMIT ?",
        (max_tries, limit),
    ).fetchall()
    return [row_to_dict(row) for row in rows]


def unrated(limit: int = 500) -> list[dict]:
    connection = connect()
    rows = connection.execute(
        "SELECT * FROM suppliers WHERE score = 0 ORDER BY updated_at DESC LIMIT ?", (limit,)
    ).fetchall()
    return [row_to_dict(row) for row in rows]


def notes_of(user_id: str) -> list[dict]:
    connection = connect()
    rows = connection.execute(
        "SELECT supplier_id, text, updated_at FROM notes WHERE user_id=? AND text != '' "
        "ORDER BY updated_at DESC",
        (user_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def save_note(user_id: str, supplier_id: str, text: str) -> dict:
    now = time.time()
    with _lock:
        connection = connect()
        connection.execute(
            "INSERT INTO notes (user_id, supplier_id, text, updated_at) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(user_id, supplier_id) DO UPDATE SET text=excluded.text, "
            "updated_at=excluded.updated_at",
            (user_id, supplier_id, text, now),
        )
        connection.commit()
    return {"supplier_id": supplier_id, "text": text, "updated_at": now}


def delete_note(user_id: str, supplier_id: str) -> None:
    with _lock:
        connection = connect()
        connection.execute(
            "DELETE FROM notes WHERE user_id=? AND supplier_id=?", (user_id, supplier_id)
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
            "111.0 * SQRT((lat - ?) * (lat - ?) + "
            "(lon - ?) * (lon - ?) * 0.33), 1) "
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


def stats() -> dict:
    connection = connect()
    row = connection.execute(
        "SELECT COUNT(*) AS total, "
        "SUM(CASE WHEN certs != '[]' THEN 1 ELSE 0 END) AS with_docs, "
        "SUM(CASE WHEN verified = 1 THEN 1 ELSE 0 END) AS verified, "
        "SUM(CASE WHEN enriched_at > 0 THEN 1 ELSE 0 END) AS enriched, "
        "SUM(CASE WHEN egrul_name != '' THEN 1 ELSE 0 END) AS with_egrul, "
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
        "withEgrul": row["with_egrul"] or 0,
        "withPhone": row["with_phone"] or 0,
        "producers": row["producers"] or 0,
        "wholesale": row["wholesale"] or 0,
        "retail": row["retail"] or 0,
        "citiesIndexed": cities or 0,
    }


def _encode(value):
    if isinstance(value, (list, tuple, dict)):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, bool):
        return 1 if value else 0
    return value
