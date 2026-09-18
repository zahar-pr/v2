import asyncio
import re

SEARCH_URL = "https://egrul.nalog.ru/"
RESULT_URL = "https://egrul.nalog.ru/search-result/{token}"
CARD_URL = "https://egrul.nalog.ru/index.html?query={query}"
ATTEMPTS = 7
MIN_KEY = 8
PAUSE = 1.2
FORMS = re.compile(
    r"^(ООО|ОАО|ЗАО|ПАО|АО|ИП|ПО|НАО|ТОО|общество с ограниченной ответственностью|"
    r"акционерное общество|публичное акционерное общество|потребительское общество)\s*",
    re.I,
)
NOISE = re.compile(r"[^а-яёa-z0-9]+", re.I)
ROLE = re.compile(r"^([^:]{3,60}):\s*(.+)$")


async def lookup(session, supplier: dict, region_code: str = "") -> dict | None:
    inn = (supplier.get("inn") or "").strip()
    if inn:
        rows = await _search(session, inn, "")
        if rows:
            return _to_record(supplier, rows[0], inn)

    name = supplier.get("name") or ""
    if len(_key(name)) < 4:
        return None

    rows = await _search(session, name, region_code)
    row = _match(name, rows)
    if row is None:
        return None
    return _to_record(supplier, row, row.get("i", ""))


async def _search(session, query: str, region_code: str) -> list[dict]:
    payload = {
        "vyp3CaptchaToken": "",
        "page": "",
        "query": query,
        "region": region_code,
        "PreparedQuery": "",
    }
    try:
        async with session.post(SEARCH_URL, data=payload) as response:
            answer = await response.json(content_type=None)
    except Exception:
        return []

    token = answer.get("t")
    if not token or answer.get("captchaRequired"):
        return []

    for _ in range(ATTEMPTS):
        await asyncio.sleep(PAUSE)
        try:
            async with session.get(RESULT_URL.format(token=token)) as response:
                answer = await response.json(content_type=None)
        except Exception:
            return []
        rows = answer.get("rows") or []
        if rows:
            return rows
    return []


def _match(name: str, rows: list[dict]) -> dict | None:
    if not rows:
        return None

    wanted = _key(name)
    if len(wanted) < MIN_KEY:
        return None

    exact = [row for row in rows if _key(row.get("c") or "") == wanted]
    if len(exact) == 1:
        return exact[0]

    full = [row for row in rows if _key(row.get("n") or "") == wanted]
    return full[0] if len(full) == 1 else None


def _to_record(supplier: dict, row: dict, inn: str) -> dict:
    registered = row.get("r") or ""
    closed_at = row.get("e") or ""
    closed = bool(closed_at and closed_at != registered)
    found = {
        "egrul_name": row.get("n") or row.get("c") or "",
        "egrul_head": _head(row.get("g") or ""),
        "egrul_registered": registered,
        "egrul_closed": 1 if closed else 0,
        "sources": _sources(supplier, inn or row.get("i", "")),
    }
    if row.get("i"):
        found["inn"] = row["i"]
    if row.get("o"):
        found["ogrn"] = row["o"]
    if found["egrul_head"]:
        found["manager"] = found["egrul_head"]
    year = _year(registered)
    if year:
        found["founded"] = year
        found["years"] = f"{2026 - year} {_plural(2026 - year)} (с {year})"
    return found


def _head(raw: str) -> str:
    found = ROLE.match(raw.strip())
    if not found:
        return raw.strip()
    role, person = found.group(1).strip().lower(), found.group(2).strip()
    if "организация" in role:
        return ""
    return f"{person} ({role})"


def _year(date: str) -> int | None:
    parts = date.split(".")
    return int(parts[2]) if len(parts) == 3 and parts[2].isdigit() else None


def _key(name: str) -> str:
    return NOISE.sub("", FORMS.sub("", name.strip().strip('"«»'))).lower()


def _sources(supplier: dict, query: str) -> list[dict]:
    known = [item for item in (supplier.get("sources") or []) if item.get("id") != "egrul"]
    known.append(
        {
            "id": "egrul",
            "title": "ЕГРЮЛ (ФНС)",
            "url": CARD_URL.format(query=query),
        }
    )
    return known


def _plural(n: int) -> str:
    if n % 10 == 1 and n % 100 != 11:
        return "год"
    if 2 <= n % 10 <= 4 and not 10 <= n % 100 < 20:
        return "года"
    return "лет"
