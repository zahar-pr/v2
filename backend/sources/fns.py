import asyncio
import re

SEARCH_URL = "https://pb.nalog.ru/search-proc.json"
HOME_URL = "https://pb.nalog.ru/search.html"
CARD_URL = "https://pb.nalog.ru/company.html?token={token}"
PAGE_SIZE = 25
ATTEMPTS = 6
PAUSE = 1.6
MIN_KEY = 8
COOLDOWN = 45 * 60
_cooldown = {"until": 0.0}

FORMS = re.compile(
    r"^(ООО|ОАО|ЗАО|ПАО|АО|ИП|ПО|НАО|ТОО|НКО|АНО|КФХ|общество с ограниченной ответственностью|"
    r"акционерное общество|публичное акционерное общество|потребительское общество)\s*",
    re.I,
)
NOISE = re.compile(r"[^а-яёa-z0-9]+", re.I)

FOOD_OKVED = ("10.", "11.", "01.1", "01.2", "01.4", "01.5", "03.", "46.17", "46.21", "46.3")
PACKAGING_OKVED = ("17.21", "17.29", "22.22", "23.13", "46.76")
RETAIL_OKVED = ("47.",)

OKVED_CATEGORIES = (
    ("10.1", "meat"),
    ("10.2", "fish"),
    ("10.3", "vegetables"),
    ("10.4", "spices"),
    ("10.5", "dairy"),
    ("10.6", "grain"),
    ("10.7", "bakery"),
    ("10.82", "confectionery"),
    ("10.83", "spices"),
    ("10.84", "spices"),
    ("10.85", "frozen"),
    ("10.86", "spices"),
    ("10.89", "spices"),
    ("11.", "drinks"),
    ("01.1", "vegetables"),
    ("01.2", "vegetables"),
    ("01.4", "meat"),
    ("01.5", "meat"),
    ("03.", "fish"),
    ("46.17", "wholesale"),
    ("46.21", "grain"),
    ("46.31", "vegetables"),
    ("46.32", "meat"),
    ("46.33", "dairy"),
    ("46.34", "drinks"),
    ("46.36", "confectionery"),
    ("46.37", "spices"),
    ("46.38", "fish"),
    ("46.39", "wholesale"),
    ("17.21", "packaging"),
    ("17.29", "packaging"),
    ("22.22", "packaging"),
    ("23.13", "packaging"),
    ("46.76", "packaging"),
)

DISCOVERY_QUERIES = (
    "хлебозавод",
    "хлебокомбинат",
    "пекарня производство",
    "кондитерская фабрика",
    "мясокомбинат",
    "мясоперерабатывающий",
    "птицефабрика",
    "молочный комбинат",
    "молокозавод",
    "маслосырзавод",
    "сыродельный",
    "рыбокомбинат",
    "рыбозавод",
    "консервный завод",
    "овощная база",
    "тепличный комбинат",
    "агрокомплекс",
    "агрофирма",
    "мукомольный",
    "крупяной завод",
    "элеватор",
    "пивоваренный завод",
    "завод напитков",
    "минеральная вода завод",
    "макаронная фабрика",
    "пищевой комбинат",
    "комбинат питания",
    "оптовая база продуктов",
    "торговый дом продукты",
    "пищевые ингредиенты",
    "продукты оптом",
    "гофротара",
    "упаковка пищевая",
    "полимерная упаковка",
)


def _needs_captcha(answer: dict) -> bool:
    if answer.get("captchaRequired"):
        return True
    errors = answer.get("ERRORS") or {}
    return any("aptcha" in key for key in errors)


def session_headers() -> dict:
    return {
        "Accept": "application/json",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": HOME_URL,
    }


async def _ask(session, payload: dict) -> dict:
    try:
        async with session.post(SEARCH_URL, data=payload, headers=session_headers()) as response:
            answer = await response.json(content_type=None)
    except Exception:
        return {}

    if _needs_captcha(answer):
        return {"captcha": True}

    token = answer.get("id")
    if not token:
        return {}

    for _ in range(ATTEMPTS):
        await asyncio.sleep(PAUSE)
        try:
            async with session.post(
                SEARCH_URL, data={"id": token, "method": "get-response"}, headers=session_headers()
            ) as response:
                if response.status != 200:
                    continue
                answer = await response.json(content_type=None)
        except Exception:
            return {}
        if (answer.get("ul") or {}).get("data"):
            return answer
    return answer


async def lookup(session, supplier: dict, region_code: str = "") -> dict | None:
    inn = (supplier.get("inn") or "").strip()
    if inn:
        rows = await _rows(session, inn, "")
        if rows:
            return _to_record(supplier, rows[0])

    name = supplier.get("name") or ""
    if len(_key(name)) < MIN_KEY:
        return None

    rows = await _rows(session, name, region_code)
    found = _match(name, rows)
    return _to_record(supplier, found) if found else None


async def discover(session, region_code: str, query: str, page: int = 1) -> list[dict]:
    rows = await _rows(session, query, region_code, page)
    found = []
    for row in rows:
        okved = (row.get("okved2main") or "").strip()
        if not okved or not _is_supplier(okved):
            continue
        found.append(row)
    return found


async def _rows(session, query: str, region_code: str, page: int = 1) -> list[dict]:
    if _cooldown["until"] > asyncio.get_event_loop().time():
        return []
    payload = {
        "mode": "search-all",
        "queryAll": query[:120],
        "page": str(page),
        "pageSize": str(PAGE_SIZE),
    }
    if region_code:
        payload["region"] = region_code
    answer = await _ask(session, payload)
    if answer.get("captcha"):
        _cooldown["until"] = asyncio.get_event_loop().time() + COOLDOWN
        return []
    return ((answer.get("ul") or {}).get("data")) or []


def _match(name: str, rows: list[dict]) -> dict | None:
    wanted = _key(name)
    exact = [row for row in rows if _key(row.get("namec") or "") == wanted]
    if len(exact) == 1:
        return exact[0]
    full = [row for row in rows if _key(row.get("namep") or "") == wanted]
    return full[0] if len(full) == 1 else None


def _to_record(supplier: dict, row: dict) -> dict:
    okved = (row.get("okved2main") or "").strip()
    found = {
        "legal_name": row.get("namep") or row.get("namec") or "",
        "legal_status": row.get("sulst_name_ex") or "",
        "legal_active": 0 if row.get("pr_liq") == "1" else 1,
        "okved": okved,
        "okved_name": row.get("okved2mainname") or "",
        "sources": _sources(supplier, row),
    }
    if row.get("inn"):
        found["inn"] = row["inn"]
    if row.get("ogrn"):
        found["ogrn"] = row["ogrn"]
    year = _year(row.get("dtreg") or "")
    if year:
        found["founded"] = year
        found["years"] = f"{2026 - year} {_plural(2026 - year)} (с {year})"
    return found


def display_name(row: dict) -> str:
    raw = (row.get("namec") or "").strip()
    if not raw or len(FORMS.sub("", raw).strip(' "«»')) < 3:
        raw = (row.get("namep") or "").strip()
    clean = FORMS.sub("", raw).strip(' "«»').strip()
    if not clean:
        return raw.strip(' "«»')
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


def category_of(okved: str) -> str:
    for prefix, category in OKVED_CATEGORIES:
        if okved.startswith(prefix):
            return category
    return ""


def kind_of(okved: str) -> str:
    if okved.startswith(RETAIL_OKVED):
        return "retail"
    if okved.startswith(("46.",)):
        return "wholesale"
    if okved.startswith(FOOD_OKVED) or okved.startswith(PACKAGING_OKVED):
        return "producer"
    return "unknown"


def _is_supplier(okved: str) -> bool:
    if okved.startswith(RETAIL_OKVED):
        return False
    return okved.startswith(FOOD_OKVED) or okved.startswith(PACKAGING_OKVED)


def _year(date: str) -> int | None:
    parts = date.split(".")
    return int(parts[2]) if len(parts) == 3 and parts[2].isdigit() else None


def _key(name: str) -> str:
    return NOISE.sub("", FORMS.sub("", (name or "").strip().strip('"«»'))).lower()


def _sources(supplier: dict, row: dict) -> list[dict]:
    known = [item for item in (supplier.get("sources") or []) if item.get("id") != "fns"]
    token = row.get("token") or ""
    known.append(
        {
            "id": "fns",
            "title": "ФНС: Прозрачный бизнес",
            "url": CARD_URL.format(token=token) if token else HOME_URL,
        }
    )
    return known


def _plural(n: int) -> str:
    if n % 10 == 1 and n % 100 != 11:
        return "год"
    if 2 <= n % 10 <= 4 and not 10 <= n % 100 < 20:
        return "года"
    return "лет"
