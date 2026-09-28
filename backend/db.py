import json
import os
import sqlite3
import threading

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


JSON_FIELDS = ("phones", "emails", "certs", "sources", "socials", "clients", "incident")


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
    # кураторский слой: проверенные поставщики сетей и компании с санкциями
    ("trust_tier", "TEXT NOT NULL DEFAULT ''"),
    ("trust_note", "TEXT NOT NULL DEFAULT ''"),
    ("clients", "TEXT NOT NULL DEFAULT '[]'"),
    ("incident", "TEXT NOT NULL DEFAULT '[]'"),
)


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


_lock = threading.Lock()


_connection: sqlite3.Connection | None = None


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


def _encode(value):
    if isinstance(value, (list, tuple, dict)):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, bool):
        return 1 if value else 0
    return value
