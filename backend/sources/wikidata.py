from urllib.parse import urlsplit

SEARCH_URL = "https://www.wikidata.org/w/api.php"
LIMIT = 5
WEBSITE = "P856"
INCEPTION = "P571"


async def enrich(session, supplier: dict) -> dict | None:
    website = supplier.get("website") or ""
    if not website:
        return None

    host = _host(website)
    if not host:
        return None

    ids = await _search(session, supplier["name"])
    if not ids:
        return None

    entities = await _entities(session, ids)
    for entity_id, entity in entities.items():
        claims = entity.get("claims") or {}
        sites = [_value(claim) for claim in claims.get(WEBSITE, [])]
        if not any(_host(site) == host for site in sites if site):
            continue
        found: dict = {
            "sources": _sources(supplier, entity_id),
            "confirmed": True,
        }
        year = _year(claims.get(INCEPTION, []))
        if year:
            found["founded"] = year
            found["years"] = f"{2026 - year} лет (с {year})"
        return found
    return None


async def _search(session, name: str) -> list[str]:
    params = {
        "action": "wbsearchentities",
        "search": name[:60],
        "language": "ru",
        "uselang": "ru",
        "format": "json",
        "limit": LIMIT,
    }
    try:
        async with session.get(SEARCH_URL, params=params, timeout=8) as response:
            answer = await response.json(content_type=None)
    except Exception:
        return []
    return [item["id"] for item in answer.get("search", [])]


async def _entities(session, ids: list[str]) -> dict:
    params = {
        "action": "wbgetentities",
        "ids": "|".join(ids),
        "props": "claims",
        "format": "json",
    }
    try:
        async with session.get(SEARCH_URL, params=params, timeout=10) as response:
            answer = await response.json(content_type=None)
    except Exception:
        return {}
    return answer.get("entities") or {}


def _value(claim: dict):
    return ((claim.get("mainsnak") or {}).get("datavalue") or {}).get("value")


def _year(claims: list) -> int | None:
    for claim in claims:
        value = _value(claim)
        if isinstance(value, dict) and value.get("time"):
            digits = value["time"].lstrip("+")[:4]
            if digits.isdigit():
                return int(digits)
    return None


def _host(url: str) -> str:
    if not url:
        return ""
    if "//" not in url:
        url = "https://" + url
    return urlsplit(url).netloc.lower().replace("www.", "")


def _sources(supplier: dict, entity_id: str) -> list[dict]:
    known = [item for item in (supplier.get("sources") or []) if item.get("id") != "wikidata"]
    known.append(
        {
            "id": "wikidata",
            "title": "Wikidata",
            "url": f"https://www.wikidata.org/wiki/{entity_id}",
        }
    )
    return known
