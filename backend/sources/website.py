import html
import re
from html.parser import HTMLParser
from urllib.parse import unquote, urljoin, urlsplit

import domain
from domain import haystack

MAX_BYTES = 600_000
PAGE_TIMEOUT = 20
EXTRA_PAGES = 2
CONTACT_HINTS = (
    "контакт",
    "contact",
    "kontakt",
    "реквизит",
    "rekvizit",
    "о-компании",
    "o-kompanii",
    "about",
    "о-нас",
    "opt",
    "оптов",
    "dostavka",
    "доставк",
    "sertifikat",
    "сертификат",
    "качеств",
)

TAGS = re.compile(r"<(script|style|noscript)[^>]*>.*?</\1>", re.I | re.S)
COMMENTS = re.compile(r"<!--.*?-->", re.S)
ANY_TAG = re.compile(r"<[^>]+>")
SPACES = re.compile(r"[\s ]+")
LINKS = re.compile(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.{0,120}?)</a>', re.I | re.S)
DESCRIPTION = re.compile(
    r'<meta[^>]+(?:name|property)=["\'](?:description|og:description)["\'][^>]*'
    r'content=["\']([^"\']{40,400})["\']',
    re.I,
)
TITLE = re.compile(r"<title[^>]*>(.{10,200}?)</title>", re.I | re.S)

EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,10}")
EMAIL_JUNK = re.compile(r"\.(png|jpe?g|gif|svg|webp|css|js)$|sentry|wixpress|example\.|@2x", re.I)
PHONE = re.compile(r"(?:\+7|8)[\s\-(]*(\d{3})[\s\-)]*(\d{3})[\s\-]*(\d{2})[\s\-]*(\d{2})")
INN = re.compile(r"ИНН[\s:№]*(\d{10}|\d{12})", re.I)
OGRN = re.compile(r"ОГРН(?:ИП)?[\s:№]*(\d{13}|\d{15})", re.I)

CERTS = (
    (re.compile(r"ТР\s?ТС|технически[йх]\s+регламент", re.I), "Декларация ТР ТС"),
    (re.compile(r"ХАССП|HACCP", re.I), "ХАССП"),
    (re.compile(r"ISO\s?22000", re.I), "ISO 22000"),
    (re.compile(r"ISO\s?9001", re.I), "ISO 9001"),
    (re.compile(r"халяль|halal", re.I), "Сертификат халяль"),
    (re.compile(r"кошер", re.I), "Кошерный сертификат"),
    (
        re.compile(r"ветеринарн\w*\s+(?:сертификат|свидетельств|сопроводительн)", re.I),
        "Ветеринарные документы",
    ),
    (re.compile(r"ФГИС|Меркури[йи]", re.I), "ФГИС «Меркурий»"),
    (re.compile(r"деклараци\w*\s+о\s+соответствии", re.I), "Декларация о соответствии"),
    (re.compile(r"сертификат\w*\s+соответствия", re.I), "Сертификат соответствия"),
    (re.compile(r"органик|organic|эко-?сертификат", re.I), "Органик-сертификат"),
    (re.compile(r"протокол\w*\s+испытани", re.I), "Протокол испытаний"),
)

UNITS = {
    "кг": ("кг", 1.0),
    "килограмм": ("кг", 1.0),
    "т": ("т", 1000.0),
    "тонн": ("т", 1000.0),
    "шт": ("шт", 0.5),
    "штук": ("шт", 0.5),
    "л": ("л", 1.0),
    "литр": ("л", 1.0),
    "упак": ("упак", 5.0),
    "уп": ("упак", 5.0),
    "коробк": ("коробок", 10.0),
    "паллет": ("паллет", 500.0),
    "ящик": ("ящиков", 15.0),
    "бутыл": ("бутылок", 0.5),
}
FOOD_WORDS = re.compile(
    r"продукт|пищев|food|опт\\b|оптов|поставк|производств|ингредиент|сырь[ёе]|"
    r"молок|мясн|хлеб|выпечк|кондитер|напитк|упаковк|фасовк|склад",
    re.I,
)
UNIT_WORDS = "кг|килограмм\\w*|тонн\\w*|т|шт\\w*|л|литр\\w*|упак\\w*|уп|коробк\\w*|паллет\\w*|ящик\\w*|бутыл\\w*"

MOQ_LINE = re.compile(
    r"(?:минимальн\w*\s+(?:заказ|парти\w*|отгрузк\w*|объ[её]м)|мин\.?\s*заказ|отгружаем\s+от|"
    r"заказ\s+от)[^.!?\n]{0,60}",
    re.I,
)
MOQ_VALUE = re.compile(rf"от\s*(\d[\d\s.,]*)\s*({UNIT_WORDS})", re.I)
PRICE_VALUE = re.compile(
    r"от\s*(\d[\d\s.,]*)\s*(?:₽|руб\w*|р\.)\s*(?:/|за\s+)\s*(кг|шт\w*|л|тонн\w*|т|упак\w*|уп)",
    re.I,
)
PRICE_REQUEST = re.compile(r"(?:цен\w*|прайс\w*|стоимост\w*)[^.!?\n]{0,20}по\s+запросу", re.I)
DELIVERY_LINE = re.compile(
    r"(?:доставка|отгрузка|самовывоз)[^.!?\n]{0,70}",
    re.I,
)
DELIVERY_FAST = re.compile(r"в\s+день\s+заказа|на\s+следующий\s+день|1[–—-]2\s+дн|ежедневн", re.I)
NAV_WORDS = re.compile(
    r"франшиз|вакансі|ваканс|контакты|главная|о\s+компании|каталог|новости|корзина|"
    r"личный кабинет|войти|регистрац|меню|блог|отзывы|акции|войдите",
    re.I,
)
DELIVERY_WORDS = re.compile(
    r"самовывоз|транспортн|курьер|бесплатн|по\s+росси|рефрижератор|собственн\w+\s+транспорт|"
    r"своя\s+логистик|тк\b|сдэк|деловые линии|пэк\b",
    re.I,
)
GEO_ALL = re.compile(r"по\s+всей\s+Росси|доставка\s+по\s+РФ|всей\s+территории\s+Росси", re.I)
GEO_AREA = re.compile(
    r"по\s+([А-ЯЁ][а-яё]+(?:ой|ской|кой)\s+(?:области|край|краю|республике))|"
    r"\b(ЦФО|СЗФО|ЮФО|ПФО|УФО|СФО|ДФО|СКФО)\b"
)
FOUNDED = re.compile(
    r"(?:с|основан\w*\s+в|работаем\s+с|на\s+рынке\s+с)\s*(19\d{2}|20[0-2]\d)\s*год", re.I
)
YEARS_ON_MARKET = re.compile(
    r"(?:более\s+)?(\d{1,2})\s*(?:лет|года)\s+(?:на\s+рынке|опыта|работаем)", re.I
)


async def enrich(session, supplier: dict) -> dict | None:
    start = supplier.get("website") or ""
    if not start:
        return None

    pages = await _read_site(session, start)
    if not pages:
        return None

    raw = " ".join(page["raw"] for page in pages)
    text = SPACES.sub(" ", " ".join(page["text"] for page in pages))
    about = _about(raw, text)
    text = f"{text} {about}".strip()
    if not text or not _relevant(supplier, text.lower()):
        return None

    emails = _emails(text, urlsplit(start).netloc)
    phones = _phones(text)
    certs = [title for pattern, title in CERTS if pattern.search(text)]

    found = {"sources": _sources(supplier, start, pages), "certs": certs}
    if emails:
        found["emails"] = _merge(supplier.get("emails", []), emails)
    if phones:
        found["phones"] = _merge(supplier.get("phones", []), phones)
    if about:
        found["about"] = about

    found.update(_requisites(text))
    for part in (_moq(text), _price(text), _years(text)):
        if part:
            found.update(part)
    for field, value in (("delivery", _delivery(text)), ("geo", _geo(text))):
        if value:
            found[field] = value

    found["haystack"] = _haystack({**supplier, **found}, certs, found)
    found["confirmed"] = _confirms(supplier, text.lower(), emails, phones)
    return found


def _requisites(text: str) -> dict:
    found = {}
    inn = INN.search(text)
    if inn:
        found["inn"] = inn.group(1)
    ogrn = OGRN.search(text)
    if ogrn:
        found["ogrn"] = ogrn.group(1)
    return found


def _haystack(merged: dict, certs: list[str], found: dict) -> str:
    parts = [haystack(merged), " ".join(certs), found.get("about", ""), found.get("geo", "")]
    return " ".join(parts).lower()[:2000]


def _relevant(supplier: dict, lowered: str) -> bool:
    words = [word for word in re.split(r"\W+", supplier.get("name", "").lower()) if len(word) > 3]
    if any(word in lowered for word in words):
        return True
    return bool(FOOD_WORDS.search(lowered))


async def _read_site(session, start: str) -> list[dict]:
    home = await _read_page(session, start)
    if not home:
        return []

    pages = [home]
    base = start
    seen = {start.rstrip("/")}
    for link in _contact_links(home["raw"], base):
        if len(pages) > EXTRA_PAGES:
            break
        if link.rstrip("/") in seen:
            continue
        seen.add(link.rstrip("/"))
        page = await _read_page(session, link)
        if page:
            pages.append(page)
    return pages


async def _read_page(session, url: str) -> dict | None:
    try:
        async with session.get(url, timeout=PAGE_TIMEOUT, allow_redirects=True) as response:
            if response.status != 200:
                return None
            kind = (response.headers.get("Content-Type") or "").lower()
            if "html" not in kind and "text" not in kind:
                return None
            body = await response.content.read(MAX_BYTES)
    except Exception:
        return None

    raw = _decode(body)
    return {"url": url, "raw": raw, "text": _text(raw)}


def _decode(body: bytes) -> str:
    for encoding in ("utf-8", "cp1251"):
        try:
            return body.decode(encoding)
        except UnicodeDecodeError:
            continue
    return body.decode("utf-8", "ignore")


class _Reader(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript", "svg"):
            self.skip += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript", "svg") and self.skip:
            self.skip -= 1

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def _text(raw: str) -> str:
    reader = _Reader()
    try:
        reader.feed(COMMENTS.sub(" ", raw))
        reader.close()
        clean = " ".join(reader.parts)
    except Exception:
        clean = html.unescape(ANY_TAG.sub(" ", TAGS.sub(" ", COMMENTS.sub(" ", raw))))
    return SPACES.sub(" ", clean)


def _contact_links(raw: str, base: str) -> list[str]:
    host = urlsplit(base).netloc
    found: list[str] = []
    for href, label in LINKS.findall(raw):
        if href.startswith(("mailto:", "tel:", "#", "javascript:")):
            continue
        target = f"{unquote(href)} {_text(label)}".lower()
        if not any(hint in target for hint in CONTACT_HINTS):
            continue
        full = urljoin(base, href)
        if urlsplit(full).netloc != host or full in found:
            continue
        found.append(full)
    found.sort(key=_link_rank)
    return found[:6]


def _link_rank(url: str) -> int:
    low = unquote(url).lower()
    for position, hint in enumerate(CONTACT_HINTS):
        if hint in low:
            return position
    return len(CONTACT_HINTS)


def _emails(text: str, host: str) -> list[str]:
    found: list[str] = []
    for item in EMAIL.findall(text):
        item = item.strip(".,;").lower()
        if EMAIL_JUNK.search(item) or item in found:
            continue
        found.append(item)
    domain = host.replace("www.", "")
    found.sort(key=lambda item: 0 if item.endswith(domain) else 1)
    return found[:3]


def _phones(text: str) -> list[str]:
    found: list[str] = []
    for parts in PHONE.findall(text):
        number = f"+7 {parts[0]} {parts[1]}-{parts[2]}-{parts[3]}"
        if number not in found:
            found.append(number)
    return found[:4]


def _merge(first: list[str], second: list[str]) -> list[str]:
    return list(dict.fromkeys([*first, *second]))[:5]


def _moq(text: str) -> dict | None:
    line = MOQ_LINE.search(text)
    scope = line.group(0) if line else ""
    value = MOQ_VALUE.search(scope) or (MOQ_VALUE.search(text) if line else None)
    if not value:
        return None
    number = _number(value.group(1))
    if not number:
        return None
    unit, weight = _unit(value.group(2))
    return {
        "moq": f"от {value.group(1).strip()} {unit}",
        "moq_value": number * weight,
        "moq_unit": unit,
    }


def _price(text: str) -> dict | None:
    value = PRICE_VALUE.search(text)
    if value:
        number = _number(value.group(1))
        unit, _ = _unit(value.group(2))
        return {
            "price": f"от {value.group(1).strip()} ₽/{unit}",
            "price_value": number,
            "price_unit": unit,
            "price_on_request": 0,
        }
    if PRICE_REQUEST.search(text):
        return {"price": "по запросу", "price_on_request": 1}
    return None


def _delivery(text: str) -> str:
    for line in DELIVERY_LINE.findall(text):
        clean = SPACES.sub(" ", line).strip(" -–—:;,")
        if len(clean) < 14 or len(clean) > 90:
            continue
        if NAV_WORDS.search(clean):
            continue
        if not (
            DELIVERY_FAST.search(clean) or DELIVERY_WORDS.search(clean) or re.search(r"\d", clean)
        ):
            continue
        return clean[0].upper() + clean[1:]
    return ""


def _geo(text: str) -> str:
    if GEO_ALL.search(text):
        return "Вся Россия"
    found = GEO_AREA.search(text)
    if found:
        return (found.group(1) or found.group(2) or "").strip()
    return ""


def _years(text: str) -> dict | None:
    founded = FOUNDED.search(text)
    if founded:
        year = int(founded.group(1))
        return {"founded": year, "years": domain.years_text(year)}
    on_market = YEARS_ON_MARKET.search(text)
    if on_market:
        age = int(on_market.group(1))
        return {"years": f"{age} {domain.plural(age, 'год', 'года', 'лет')}"}
    return None


def _about(raw: str, text: str) -> str:
    found = DESCRIPTION.search(raw)
    if found:
        return html.unescape(found.group(1)).strip()[:400]
    title = TITLE.search(raw)
    if title:
        clean = SPACES.sub(" ", html.unescape(title.group(1))).strip()
        if len(clean) > 30:
            return clean[:400]
    return ""


def _sources(supplier: dict, start: str, pages: list[dict]) -> list[dict]:
    return domain.with_source(
        supplier, "website", "Сайт поставщика", start, pages=[page["url"] for page in pages]
    )


def _confirms(supplier: dict, lowered: str, emails: list[str], phones: list[str]) -> bool:
    for phone in supplier.get("phones") or []:
        digits = re.sub(r"\D", "", phone)[-10:]
        if digits and any(digits == re.sub(r"\D", "", item)[-10:] for item in phones):
            return True
    for email in supplier.get("emails") or []:
        if email.lower() in lowered:
            return True
    return False


def _number(raw: str) -> float:
    clean = raw.replace(" ", "").replace(" ", "").replace(",", ".").rstrip(".")
    try:
        return float(clean)
    except ValueError:
        return 0.0


def _unit(raw: str) -> tuple[str, float]:
    low = raw.lower()
    for prefix, (title, weight) in UNITS.items():
        if low.startswith(prefix):
            return title, weight
    return low, 1.0
