import os

import catalog
from catalog import City
from domain import haystack, is_food_related, looks_wholesale, name_key
from sources.base import SupplierSource

ITEMS_URL = "https://catalog.api.2gis.com/3.0/items"
FIELDS = (
    "items.point,items.contact_groups,items.rubrics,items.reviews,"
    "items.address,items.schedule,items.org"
)
PAGE_SIZE = 50
QUERIES = {
    "wholesale": "оптовая база продуктов",
    "grain": "мука крупы оптом",
    "dairy": "молочная продукция оптом",
    "meat": "мясокомбинат оптом",
    "fish": "рыба оптом",
    "vegetables": "овощная база оптом",
    "bakery": "хлебозавод пекарня оптом",
    "confectionery": "кондитерская фабрика оптом",
    "drinks": "напитки вода оптом",
    "packaging": "пищевая упаковка оптом",
}


class TwoGisSource(SupplierSource):
    id = "2gis"
    title = "2ГИС"

    def ready(self) -> bool:
        return bool(os.environ.get("TWOGIS_KEY"))

    async def collect(self, session, city: City) -> list[dict]:
        key = os.environ.get("TWOGIS_KEY", "")
        if not key:
            return []

        found: list[dict] = []
        for category_id, query in QUERIES.items():
            items = await self._ask(session, key, city.name, query)
            for item in items:
                record = _to_record(item, city, category_id, self.title)
                if record:
                    found.append(record)
        return found

    async def _ask(self, session, key: str, city: str, query: str) -> list[dict]:
        params = {
            "q": f"{query} {city}",
            "key": key,
            "fields": FIELDS,
            "page_size": PAGE_SIZE,
            "locale": "ru_RU",
        }
        try:
            async with session.get(ITEMS_URL, params=params, timeout=12) as response:
                answer = await response.json(content_type=None)
        except Exception:
            return []
        return ((answer.get("result") or {}).get("items")) or []


def _to_record(item: dict, city: City, category_id: str, source_title: str) -> dict | None:
    name = item.get("name") or ""
    if not name or not is_food_related(name):
        return None

    contacts = _contacts(item)
    reviews = item.get("reviews") or {}
    point = item.get("point") or {}
    item_id = item.get("id") or ""
    url = f"https://2gis.ru/firm/{item_id.split('_')[0]}" if item_id else "https://2gis.ru"
    record = {
        "id": f"2gis:{item_id}",
        "name": name,
        "name_key": name_key(name),
        "city": city.name,
        "region": city.region,
        "cats": f",{category_id},",
        "cats_titles": [catalog.title(category_id)],
        "kind": _kind(item),
        "address": item.get("address_name") or city.name,
        "phones": contacts["phones"],
        "emails": contacts["emails"],
        "socials": [],
        "website": contacts["website"],
        "hours": _hours(item),
        "wholesale": looks_wholesale(name) or "опт" in (item.get("address_name") or "").lower(),
        "branches": 1,
        "lat": point.get("lat"),
        "lon": point.get("lon"),
        "source": url,
        "source_title": source_title,
        "sources": [{"id": "2gis", "title": source_title, "url": url}],
        "rating": reviews.get("general_rating"),
        "reviews": reviews.get("general_review_count"),
    }
    record["haystack"] = haystack(record)
    return record


def _contacts(item: dict) -> dict:
    phones: list[str] = []
    emails: list[str] = []
    website = ""
    for group in item.get("contact_groups") or []:
        for contact in group.get("contacts") or []:
            kind = contact.get("type")
            value = contact.get("value") or contact.get("text") or ""
            if kind == "phone" and value not in phones:
                phones.append(value)
            elif kind == "email" and value not in emails:
                emails.append(value)
            elif kind == "website" and not website:
                website = value if value.startswith("http") else f"https://{value}"
    return {"phones": phones[:4], "emails": emails[:3], "website": website}


def _kind(item: dict) -> str:
    rubrics = item.get("rubrics") or []
    return (rubrics[0].get("name") if rubrics else "") or catalog.UNKNOWN_KIND


def _hours(item: dict) -> str:
    schedule = item.get("schedule") or {}
    if schedule.get("is_24x7"):
        return "круглосуточно"
    return ""
