import json
import os
import sqlite3
import threading
import time

import scoring

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
    area TEXT NOT NULL DEFAULT '',
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
    reviews_url TEXT NOT NULL DEFAULT '',
    reviews_source TEXT NOT NULL DEFAULT '',
    reviews_checked REAL NOT NULL DEFAULT 0,
    verified INTEGER NOT NULL DEFAULT 0,
    verified_by TEXT NOT NULL DEFAULT '',
    score INTEGER NOT NULL DEFAULT 0,
    haystack TEXT NOT NULL DEFAULT '',
    score_reach INTEGER NOT NULL DEFAULT 0,
    score_volume INTEGER NOT NULL DEFAULT 0,
    score_docs INTEGER NOT NULL DEFAULT 0,
    score_logistics INTEGER NOT NULL DEFAULT 0,
    score_trust INTEGER NOT NULL DEFAULT 0,
    scored_at REAL NOT NULL DEFAULT 0,
    comments_count INTEGER NOT NULL DEFAULT 0,
    comments_rating REAL,
    distance_km REAL,
    price_list TEXT NOT NULL DEFAULT '',
    own_delivery INTEGER NOT NULL DEFAULT 0,
    egrul_checked REAL NOT NULL DEFAULT 0,
    okved TEXT NOT NULL DEFAULT '',
    okved_name TEXT NOT NULL DEFAULT '',
    legal_name TEXT NOT NULL DEFAULT '',
    legal_status TEXT NOT NULL DEFAULT '',
    legal_active INTEGER NOT NULL DEFAULT 0,
    score_reputation INTEGER NOT NULL DEFAULT 0,
    fns_checked REAL NOT NULL DEFAULT 0,
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
    supplier_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL DEFAULT '',
    author TEXT NOT NULL DEFAULT '',
    text TEXT NOT NULL DEFAULT '',
    updated_at REAL NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS checks (
    supplier_id TEXT NOT NULL,
    question TEXT NOT NULL,
    author TEXT NOT NULL DEFAULT '',
    updated_at REAL NOT NULL DEFAULT 0,
    PRIMARY KEY (supplier_id, question)
);

CREATE TABLE IF NOT EXISTS comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    author TEXT NOT NULL DEFAULT '',
    text TEXT NOT NULL,
    rating INTEGER,
    created_at REAL NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS comments_supplier ON comments(supplier_id, created_at DESC);

CREATE TABLE IF NOT EXISTS profiles (
    user_id TEXT PRIMARY KEY,
    name TEXT NOT NULL DEFAULT '',
    updated_at REAL NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS centers (
    city TEXT PRIMARY KEY,
    lat REAL NOT NULL,
    lon REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS pipeline (
    supplier_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL DEFAULT '',
    author TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'new',
    updated_at REAL NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS refreshes (
    city TEXT PRIMARY KEY,
    refreshed_at REAL NOT NULL DEFAULT 0,
    found INTEGER NOT NULL DEFAULT 0,
    note TEXT NOT NULL DEFAULT ''
);
"""

NULLABLE_FIELDS = ("lat", "lon", "distance_km")
NUMERIC_FIELDS = ("wholesale", "branches", "checked_at")

JSON_FIELDS = ("phones", "emails", "certs", "sources", "socials")

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
    "score_reputation",
)


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
    ("reviews_url", "TEXT NOT NULL DEFAULT ''"),
    ("reviews_source", "TEXT NOT NULL DEFAULT ''"),
    ("reviews_checked", "REAL NOT NULL DEFAULT 0"),
    ("comments_count", "INTEGER NOT NULL DEFAULT 0"),
    ("comments_rating", "REAL"),
    ("area", "TEXT NOT NULL DEFAULT ''"),
    ("okved", "TEXT NOT NULL DEFAULT ''"),
    ("okved_name", "TEXT NOT NULL DEFAULT ''"),
    ("legal_name", "TEXT NOT NULL DEFAULT ''"),
    ("legal_status", "TEXT NOT NULL DEFAULT ''"),
    ("legal_active", "INTEGER NOT NULL DEFAULT 0"),
    ("score_reputation", "INTEGER NOT NULL DEFAULT 0"),
    ("fns_checked", "REAL NOT NULL DEFAULT 0"),
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


DROPPED_COLUMNS = (
    "plus",
    "minus",
    "level",
    "verdict",
    "factors",
    "egrul_name",
    "egrul_head",
    "egrul_registered",
    "egrul_closed",
)


def _migrate(connection: sqlite3.Connection) -> None:
    known = {row["name"] for row in connection.execute("PRAGMA table_info(suppliers)")}
    for column, definition in ADDED_COLUMNS:
        if column not in known:
            connection.execute(f"ALTER TABLE suppliers ADD COLUMN {column} {definition}")
    for column in DROPPED_COLUMNS:
        if column in known:
            connection.execute(f"ALTER TABLE suppliers DROP COLUMN {column}")

    _rebuild_team_table(connection, "pipeline", "status")
    _rebuild_team_table(connection, "notes", "text")


def _rebuild_team_table(connection: sqlite3.Connection, table: str, value: str) -> None:
    columns = {row["name"] for row in connection.execute(f"PRAGMA table_info({table})")}
    if "author" in columns:
        return

    connection.execute(f"ALTER TABLE {table} RENAME TO {table}_old")
    connection.executescript(SCHEMA)
    connection.execute(
        f"INSERT OR REPLACE INTO {table} (supplier_id, user_id, author, {value}, updated_at) "
        f"SELECT supplier_id, user_id, '', {value}, updated_at FROM {table}_old "
        f"WHERE updated_at = (SELECT MAX(updated_at) FROM {table}_old AS inner "
        f"WHERE inner.supplier_id = {table}_old.supplier_id)"
    )
    connection.execute(f"DROP TABLE {table}_old")


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
            "score_logistics=?, score_trust=?, score_reputation=?, score=?, scored_at=?, "
            "rating=CASE WHEN reviews IS NULL THEN ? ELSE rating END WHERE id=?",
            (
                scores["reach"],
                scores["volume"],
                scores["docs"],
                scores["logistics"],
                scores["trust"],
                scores["reputation"],
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


def comments_of(supplier_id: str) -> list[dict]:
    connection = connect()
    rows = connection.execute(
        "SELECT * FROM comments WHERE supplier_id=? ORDER BY created_at DESC LIMIT 100",
        (supplier_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def comments_by(user_id: str, supplier_id: str) -> int:
    connection = connect()
    return connection.execute(
        "SELECT COUNT(*) FROM comments WHERE user_id=? AND supplier_id=?",
        (user_id, supplier_id),
    ).fetchone()[0]


def add_comment(user_id: str, supplier_id: str, author: str, text: str, rating) -> dict:
    now = time.time()
    with _lock:
        connection = connect()
        cursor = connection.execute(
            "INSERT INTO comments (supplier_id, user_id, author, text, rating, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (supplier_id, user_id, author, text, rating, now),
        )
        connection.commit()
        comment_id = cursor.lastrowid
    _refresh_comment_stats(supplier_id)
    return {
        "id": comment_id,
        "supplier_id": supplier_id,
        "user_id": user_id,
        "author": author,
        "text": text,
        "rating": rating,
        "created_at": now,
    }


def delete_comment(user_id: str, comment_id: int) -> str:
    with _lock:
        connection = connect()
        row = connection.execute(
            "SELECT supplier_id FROM comments WHERE id=? AND user_id=?", (comment_id, user_id)
        ).fetchone()
        if row is None:
            return ""
        connection.execute("DELETE FROM comments WHERE id=?", (comment_id,))
        connection.commit()
    _refresh_comment_stats(row["supplier_id"])
    return row["supplier_id"]


def _refresh_comment_stats(supplier_id: str) -> None:
    with _lock:
        connection = connect()
        row = connection.execute(
            "SELECT COUNT(*) AS n, AVG(rating) AS avg_rating FROM comments WHERE supplier_id=?",
            (supplier_id,),
        ).fetchone()
        connection.execute(
            "UPDATE suppliers SET comments_count=?, comments_rating=?, scored_at=0 WHERE id=?",
            (
                row["n"] or 0,
                round(row["avg_rating"], 1) if row["avg_rating"] else None,
                supplier_id,
            ),
        )
        connection.commit()


def profile_of(user_id: str) -> str:
    connection = connect()
    row = connection.execute("SELECT name FROM profiles WHERE user_id=?", (user_id,)).fetchone()
    return row["name"] if row else ""


def save_profile(user_id: str, name: str) -> str:
    with _lock:
        connection = connect()
        connection.execute(
            "INSERT INTO profiles (user_id, name, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET name=excluded.name, updated_at=excluded.updated_at",
            (user_id, name, time.time()),
        )
        connection.commit()
    return name


def statuses_of() -> dict:
    connection = connect()
    rows = connection.execute("SELECT supplier_id, status FROM pipeline").fetchall()
    return {row["supplier_id"]: row["status"] for row in rows}


def status_authors() -> dict:
    connection = connect()
    rows = connection.execute("SELECT supplier_id, author, updated_at FROM pipeline").fetchall()
    return {row["supplier_id"]: dict(row) for row in rows}


def set_status(user_id: str, author: str, supplier_id: str, status: str) -> dict:
    now = time.time()
    with _lock:
        connection = connect()
        if status in ("", "new"):
            connection.execute("DELETE FROM pipeline WHERE supplier_id=?", (supplier_id,))
        else:
            connection.execute(
                "INSERT INTO pipeline (supplier_id, user_id, author, status, updated_at) "
                "VALUES (?, ?, ?, ?, ?) ON CONFLICT(supplier_id) DO UPDATE SET "
                "user_id=excluded.user_id, author=excluded.author, status=excluded.status, "
                "updated_at=excluded.updated_at",
                (supplier_id, user_id, author, status, now),
            )
        connection.commit()
    return {"supplier_id": supplier_id, "status": status or "new", "updated_at": now}


def status_counts() -> dict:
    connection = connect()
    rows = connection.execute(
        "SELECT status, COUNT(*) AS n FROM pipeline GROUP BY status"
    ).fetchall()
    return {row["status"]: row["n"] for row in rows}


def pending_reviews(limit: int) -> list[dict]:
    connection = connect()
    rows = connection.execute(
        "SELECT * FROM suppliers WHERE reviews_checked = 0 AND kind_class != 'retail' "
        "ORDER BY " + KIND_ORDER + ", score DESC LIMIT ?",
        (limit,),
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


def pending_enrichment(limit: int, max_tries: int = 3) -> list[dict]:
    connection = connect()
    rows = connection.execute(
        "SELECT * FROM suppliers WHERE website != '' AND enriched_at = 0 AND enrich_tries < ? "
        "ORDER BY enrich_tries ASC, " + KIND_ORDER + ", score DESC LIMIT ?",
        (max_tries, limit),
    ).fetchall()
    return [row_to_dict(row) for row in rows]


def notes_of() -> list[dict]:
    connection = connect()
    rows = connection.execute(
        "SELECT supplier_id, text, author, updated_at FROM notes WHERE text != '' "
        "ORDER BY updated_at DESC"
    ).fetchall()
    return [dict(row) for row in rows]


def save_note(user_id: str, author: str, supplier_id: str, text: str) -> dict:
    now = time.time()
    with _lock:
        connection = connect()
        connection.execute(
            "INSERT INTO notes (supplier_id, user_id, author, text, updated_at) "
            "VALUES (?, ?, ?, ?, ?) ON CONFLICT(supplier_id) DO UPDATE SET "
            "user_id=excluded.user_id, author=excluded.author, text=excluded.text, "
            "updated_at=excluded.updated_at",
            (supplier_id, user_id, author, text, now),
        )
        connection.commit()
    return {"supplier_id": supplier_id, "text": text, "author": author, "updated_at": now}


def delete_note(supplier_id: str) -> None:
    with _lock:
        connection = connect()
        connection.execute("DELETE FROM notes WHERE supplier_id=?", (supplier_id,))
        connection.commit()


def checks_of(supplier_id: str) -> list[str]:
    connection = connect()
    rows = connection.execute(
        "SELECT question FROM checks WHERE supplier_id=?", (supplier_id,)
    ).fetchall()
    return [row["question"] for row in rows]


def checks_count() -> dict:
    connection = connect()
    rows = connection.execute(
        "SELECT supplier_id, COUNT(*) AS n FROM checks GROUP BY supplier_id"
    ).fetchall()
    return {row["supplier_id"]: row["n"] for row in rows}


def set_check(supplier_id: str, question: str, done: bool, author: str) -> None:
    with _lock:
        connection = connect()
        if done:
            connection.execute(
                "INSERT INTO checks (supplier_id, question, author, updated_at) "
                "VALUES (?, ?, ?, ?) ON CONFLICT(supplier_id, question) DO UPDATE SET "
                "author=excluded.author, updated_at=excluded.updated_at",
                (supplier_id, question, author, time.time()),
            )
        else:
            connection.execute(
                "DELETE FROM checks WHERE supplier_id=? AND question=?", (supplier_id, question)
            )
        connection.commit()


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


def _encode(value):
    if isinstance(value, (list, tuple, dict)):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, bool):
        return 1 if value else 0
    return value
