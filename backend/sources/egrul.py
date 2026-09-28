import asyncio
import re

import domain

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
NON_COMMERCIAL = re.compile(
    r"\b(профком|профсоюз|снт\b|тсж|тсн|гск|жск|дск|товарищество собственник|"
    r"садов\w+ некоммерч|первичная организация|фонд\b|ассоциация|союз\b|"
    r"учреждение|администрация|управление|комитет|музей|школа|детский сад|"
    r"общежитие|казенное|бюджетное|автономная некоммерч|партия|церковь|приход)",
    re.I,
)
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
    row = _match(name, rows, region_code)
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


def _match(name: str, rows: list[dict], region_code: str = "") -> dict | None:
    if not domain.distinctive(name):
        rows = [row for row in rows if domain.same_region(row.get("i"), region_code)]
    # ликвидированный тёзка из другого региона — почти наверняка не наша компания
    rows = [
        row for row in rows if not _closed(row) or domain.same_region(row.get("i"), region_code)
    ]
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


def _closed(row: dict) -> bool:
    registered = row.get("r") or ""
    return bool(row.get("e") and row.get("e") != registered)


def _to_record(supplier: dict, row: dict, inn: str) -> dict:
    closed = _closed(row)
    head = head_of(row.get("g") or "")
    found = {
        "legal_name": row.get("n") or row.get("c") or "",
        "legal_status": "Есть запись о прекращении" if closed else "Действующая организация",
        "legal_active": 0 if closed else 1,
        "sources": domain.with_source(
            supplier, "egrul", "ЕГРЮЛ (ФНС)", CARD_URL.format(query=inn or row.get("i", ""))
        ),
    }
    if head:
        found["manager"] = head
    if row.get("i"):
        found["inn"] = row["i"]
    if row.get("o"):
        found["ogrn"] = row["o"]
    year = domain.year_of(row.get("r") or "")
    if year:
        found["founded"] = year
        found["years"] = domain.years_text(year)
    return found


def head_of(raw: str) -> str:
    found = ROLE.match(raw.strip())
    if not found:
        return raw.strip()
    role, person = found.group(1).strip().lower(), found.group(2).strip()
    if "организация" in role:
        return ""
    return f"{person} ({role})"


def _key(name: str) -> str:
    return NOISE.sub("", FORMS.sub("", name.strip().strip('"«»'))).lower()


DISCOVERY = (
    ("хлебозавод", "bakery", "producer"),
    ("хлебокомбинат", "bakery", "producer"),
    ("булочно-кондитерский", "bakery", "producer"),
    ("кондитерская фабрика", "confectionery", "producer"),
    ("кондитерский комбинат", "confectionery", "producer"),
    ("шоколадная фабрика", "confectionery", "producer"),
    ("мясокомбинат", "meat", "producer"),
    ("мясоперерабатывающий", "meat", "producer"),
    ("колбасный завод", "meat", "producer"),
    ("птицефабрика", "meat", "producer"),
    ("свинокомплекс", "meat", "producer"),
    ("молочный комбинат", "dairy", "producer"),
    ("молокозавод", "dairy", "producer"),
    ("маслосырзавод", "dairy", "producer"),
    ("сыродельный", "dairy", "producer"),
    ("рыбокомбинат", "fish", "producer"),
    ("рыбозавод", "fish", "producer"),
    ("рыбопереработка", "fish", "producer"),
    ("консервный завод", "vegetables", "producer"),
    ("овощная база", "vegetables", "wholesale"),
    ("тепличный комбинат", "vegetables", "producer"),
    ("агрофирма", "vegetables", "producer"),
    ("агрокомплекс", "vegetables", "producer"),
    ("мукомольный", "grain", "producer"),
    ("крупяной завод", "grain", "producer"),
    ("элеватор", "grain", "producer"),
    ("комбинат хлебопродуктов", "grain", "producer"),
    ("пивоваренный завод", "drinks", "producer"),
    ("завод напитков", "drinks", "producer"),
    ("завод минеральных вод", "drinks", "producer"),
    ("винодельня", "drinks", "producer"),
    ("чаеразвесочная", "spices", "producer"),
    ("пищевые ингредиенты", "spices", "producer"),
    ("специи оптом", "spices", "wholesale"),
    ("хладокомбинат", "frozen", "producer"),
    ("холодильник пищевой", "frozen", "producer"),
    ("полуфабрикаты производство", "frozen", "producer"),
    ("пищевой комбинат", "wholesale", "producer"),
    ("комбинат питания", "wholesale", "producer"),
    ("оптовая база", "wholesale", "wholesale"),
    ("продукты оптом", "wholesale", "wholesale"),
    ("продовольственная компания", "wholesale", "wholesale"),
    ("торговый дом продукты", "wholesale", "wholesale"),
    ("гофротара", "packaging", "producer"),
    ("упаковка пищевая", "packaging", "producer"),
    ("тара и упаковка", "packaging", "producer"),
    ("полимерная упаковка", "packaging", "producer"),
)


async def discover(session, query: str, region_code: str, page: int = 1) -> list[dict]:
    payload = {
        "vyp3CaptchaToken": "",
        "page": str(page),
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
            return [
                row for row in rows if row.get("k") == "ul" and row.get("i") and is_commercial(row)
            ]
    return []


def display_name(row: dict) -> str:
    raw = (row.get("c") or row.get("n") or "").strip()
    return pretty(raw)


def pretty(raw: str) -> str:
    clean = FORMS.sub("", raw).strip(' "«»').strip()
    if not clean:
        clean = raw.strip(' "«»').strip()
    if not clean.isupper():
        return clean
    words = []
    for word in clean.split():
        letters = [i for i, ch in enumerate(word) if ch.isalpha()]
        if not letters:
            words.append(word)
            continue
        first = letters[0]
        words.append(word[:first] + word[first] + word[first + 1 :].lower())
    return " ".join(words)


def is_commercial(row: dict) -> bool:
    name = f"{row.get('c') or ''} {row.get('n') or ''}"
    return not NON_COMMERCIAL.search(name)
