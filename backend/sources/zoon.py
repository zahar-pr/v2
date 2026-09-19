import html
import re

import domain

SEARCH_URL = "https://zoon.ru/search/"
TIMEOUT = 20
MAX_CARDS = 12
MIN_KEY = 5

CARD = re.compile(r'<li class="minicard-item(.*?)</li>', re.S)
NAME = re.compile(r'class="title-link[^"]*"[^>]*>([^<]{2,120})<', re.S)
LINK = re.compile(r'href="(https://zoon\.ru/[^"]+/)"[^>]*class="title-link', re.S)
RATING_VAR = re.compile(r"--rating:\s*([0-9.]+)")
RATING_TEXT = re.compile(r">\s*([1-5][.,]\d)\s*<")
COUNT = re.compile(r"(\d+)\s*отзыв")
NOISE = re.compile(r"[^а-яёa-z0-9]+", re.I)


async def lookup(session, supplier: dict) -> dict | None:
    name = (supplier.get("name") or "").strip()
    if len(_key(name)) < MIN_KEY:
        return None

    where = supplier.get("city") or ""
    raw = await _search(session, f"{name} {where}".strip())
    if not raw:
        return None

    found = _match(name, _cards(raw))
    if found is None:
        return None

    result = {
        "reviews_url": found["url"],
        "reviews_source": "Zoon",
        "sources": domain.with_source(supplier, "zoon", "Отзывы на Zoon", found["url"]),
    }
    if found["rating"]:
        result["rating"] = found["rating"]
    if found["count"]:
        result["reviews"] = found["count"]
    return result if found["rating"] or found["count"] else None


async def _search(session, query: str) -> str:
    try:
        async with session.get(
            SEARCH_URL, params={"query": query[:120]}, timeout=TIMEOUT
        ) as answer:
            if answer.status != 200:
                return ""
            return await answer.text()
    except Exception:
        return ""


def _cards(raw: str) -> list[dict]:
    found = []
    for block in CARD.findall(raw)[:MAX_CARDS]:
        name = NAME.search(block)
        link = LINK.search(block)
        if not name or not link:
            continue
        rating = None
        exact = RATING_TEXT.search(block)
        if exact:
            rating = float(exact.group(1).replace(",", "."))
        else:
            rough = RATING_VAR.search(block)
            if rough:
                rating = float(rough.group(1))
        count = COUNT.search(block)
        found.append(
            {
                "name": html.unescape(name.group(1)).strip(),
                "url": link.group(1),
                "rating": round(rating, 1) if rating and 0 < rating <= 5 else None,
                "count": int(count.group(1)) if count else 0,
            }
        )
    return found


def _match(name: str, cards: list[dict]) -> dict | None:
    wanted = _key(name)
    exact = [card for card in cards if _key(card["name"]) == wanted]
    if exact:
        return exact[0]
    close = [
        card for card in cards if wanted in _key(card["name"]) or _key(card["name"]) in wanted
    ]
    return close[0] if len(close) == 1 else None


def _key(name: str) -> str:
    return NOISE.sub("", name).lower()
