import asyncio
import math

import catalog
from catalog import City
from domain import (
    PlaceNotFound,
    SourceUnavailable,
    classify,
    haystack,
    is_food_related,
    looks_food,
)
from sources.base import SupplierSource

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OVERPASS_MIRRORS = (
    "https://overpass-api.de/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
)
QUERY_TIMEOUT = 40
RESULT_LIMIT = 500
BIG_CITIES = {"Москва", "Санкт-Петербург"}
GENERIC_TAGS = {
    ("shop", "wholesale"),
    ("shop", "trade"),
    ("wholesale", "supermarket"),
    ("shop", "houseware"),
}
RADIUS_KM = 14
BIG_RADIUS_KM = 24
_centers: dict[str, tuple[float, float]] = {}


class OsmSource(SupplierSource):
    id = "osm"
    title = "OpenStreetMap"

    async def collect(self, session, city: City) -> list[dict]:
        center = await self._center(session, city.name)
        elements = await self._overpass(session, _query(city, center))
        found = [_to_record(element, city, self.title) for element in elements]
        return [item for item in found if item]

    async def center(self, session, place: str) -> tuple[float, float]:
        return await self._center(session, place)

    async def _center(self, session, place: str) -> tuple[float, float]:
        if place in _centers:
            return _centers[place]
        params = {"q": f"{place}, Россия", "format": "json", "limit": 1}
        async with session.get(NOMINATIM_URL, params=params) as response:
            found = await response.json(content_type=None)
        if not found:
            raise PlaceNotFound(place)
        _centers[place] = (float(found[0]["lat"]), float(found[0]["lon"]))
        return _centers[place]

    async def _overpass(self, session, query: str) -> list[dict]:
        tasks = [asyncio.create_task(self._ask(session, url, query)) for url in OVERPASS_MIRRORS]
        try:
            reasons: list[str] = []
            for finished in asyncio.as_completed(tasks):
                try:
                    return await finished
                except Exception as failure:
                    reasons.append(str(failure) or type(failure).__name__)
            raise SourceUnavailable("зеркала Overpass: " + ", ".join(reasons[:3]))
        finally:
            for task in tasks:
                task.cancel()

    async def _ask(self, session, url: str, query: str) -> list[dict]:
        async with session.post(url, data={"data": query}) as response:
            if response.status != 200:
                raise SourceUnavailable(f"Overpass ответил {response.status}")
            answer = await response.json(content_type=None)
        if not answer.get("elements") and answer.get("remark"):
            raise SourceUnavailable(answer["remark"])
        return answer.get("elements", [])


def _query(city: City, center: tuple[float, float]) -> str:
    lat, lon = center
    radius = BIG_RADIUS_KM if city.name in BIG_CITIES else RADIUS_KM
    degrees_lat = radius / 111.0
    degrees_lon = radius / (111.0 * max(math.cos(math.radians(lat)), 0.1))
    scope = (
        f"({lat - degrees_lat:.4f},{lon - degrees_lon:.4f},"
        f"{lat + degrees_lat:.4f},{lon + degrees_lon:.4f})"
    )
    tags = "".join(f'nwr["{key}"="{value}"]{scope};' for key, value in catalog.ALL_TAGS)
    return f"[out:json][timeout:{QUERY_TIMEOUT}];({tags});out center tags {RESULT_LIMIT};"


SOCIAL_TAGS = (
    ("contact:vk", "ВКонтакте", "https://vk.com/"),
    ("contact:telegram", "Telegram", "https://t.me/"),
    ("contact:whatsapp", "WhatsApp", "https://wa.me/"),
    ("contact:instagram", "Instagram", "https://instagram.com/"),
    ("contact:facebook", "Facebook", "https://facebook.com/"),
    ("contact:ok", "Одноклассники", "https://ok.ru/"),
)


def _socials(tags: dict) -> list[dict]:
    found = []
    for key, title, prefix in SOCIAL_TAGS:
        value = (tags.get(key) or "").strip()
        if not value:
            continue
        url = value if value.startswith("http") else prefix + value.lstrip("@/")
        found.append({"title": title, "url": url})
    return found[:4]


def _tag(tags: dict, *names: str) -> str:
    return next((tags[name] for name in names if tags.get(name)), "")


def _many(tags: dict, *names: str) -> list[str]:
    found: list[str] = []
    for name in names:
        for part in (tags.get(name) or "").split(";"):
            part = part.strip()
            if part and part not in found:
                found.append(part)
    return found


def _to_record(element: dict, city: City, source_title: str) -> dict | None:
    tags = element.get("tags") or {}
    name = _tag(tags, "name", "operator", "brand")
    cats = catalog.categories_for(tags)
    if not name or not cats or not is_food_related(name) or not _looks_like_food(tags, name):
        return None

    kind_key, kind_value = _kind(tags)
    kind_pair = f"{kind_key}={kind_value}" if kind_key else ""
    kind_class = classify(kind_pair, name)
    osm_id = f"{element['type']}/{element['id']}"
    url = f"https://www.openstreetmap.org/{osm_id}"
    center = element.get("center") or {}

    record = {
        "id": f"osm:{osm_id}",
        "name": name,
        "name_key": "",
        "city": city.name,
        "region": city.region,
        "cats": "," + ",".join(cats) + ",",
        "cats_titles": [catalog.title(item) for item in cats],
        "kind": catalog.KIND_TITLES.get(kind_value, kind_value or catalog.UNKNOWN_KIND),
        "kind_tag": kind_pair,
        "kind_class": kind_class,
        "address": _address(tags, city),
        "phones": _many(tags, "phone", "contact:phone", "contact:mobile"),
        "emails": _many(tags, "email", "contact:email"),
        "socials": _socials(tags),
        "website": _website(tags),
        "hours": _tag(tags, "opening_hours"),
        "wholesale": kind_class in ("producer", "wholesale"),
        "branches": 1,
        "lat": element.get("lat") or center.get("lat"),
        "lon": element.get("lon") or center.get("lon"),
        "source": url,
        "source_title": source_title,
        "sources": [{"id": "osm", "title": source_title, "url": url}],
    }
    record["haystack"] = haystack(record)
    return record


def _looks_like_food(tags: dict, name: str) -> bool:
    matched = {
        (key, value) for key, value in tags.items() if (key, value) in catalog.TAG_CATEGORIES
    }
    if not matched or not matched <= GENERIC_TAGS:
        return True

    about = " ".join(
        part
        for part in (
            name,
            tags.get("brand", ""),
            tags.get("description", ""),
            tags.get("wholesale", ""),
            tags.get("shop", ""),
        )
        if part
    )
    return looks_food(about)


def _kind(tags: dict) -> tuple[str, str]:
    for key in ("craft", "industrial", "man_made", "shop", "wholesale", "office"):
        if tags.get(key):
            return key, tags[key]
    return "", ""


def _website(tags: dict) -> str:
    found = _tag(tags, "website", "contact:website", "url")
    if found and not found.startswith("http"):
        return "https://" + found
    return found


def _address(tags: dict, city: City) -> str:
    parts = (
        _tag(tags, "addr:city") or city.name,
        _tag(tags, "addr:street"),
        _tag(tags, "addr:housenumber"),
    )
    return ", ".join(part for part in parts if part)
