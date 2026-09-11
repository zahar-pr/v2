import asyncio
import math

import aiohttp
from catalog import KIND_TITLES, UNKNOWN_KIND, Category
from domain import PlaceNotFound, SourceUnavailable, Supplier, looks_wholesale
from sources.base import SupplierSource

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OVERPASS_MIRRORS = (
    "https://overpass-api.de/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
)
USER_AGENT = "SupplierFinder/0.1 (food supplier search, MVP)"
REQUEST_TIMEOUT = 25
QUERY_TIMEOUT = 20
RESULT_LIMIT = 60
RADIUS_KM = 12


class OsmSource(SupplierSource):
    id = "osm"
    title = "OpenStreetMap"

    async def search(self, category: Category, place: str) -> list[Supplier]:
        session = aiohttp.ClientSession(
            headers={"User-Agent": USER_AGENT},
            timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
        )
        try:
            async with session:
                place_name, center = await self._geocode(session, place)
                elements = await self._overpass(session, _query(category, center))
        except (PlaceNotFound, SourceUnavailable):
            raise
        except Exception as error:
            raise SourceUnavailable(str(error) or type(error).__name__) from error
        suppliers = (_to_supplier(element, place_name, self.title) for element in elements)
        return [supplier for supplier in suppliers if supplier]

    async def _geocode(self, session: aiohttp.ClientSession, place: str) -> tuple[str, tuple]:
        params = {"q": place, "format": "json", "limit": 1}
        async with session.get(NOMINATIM_URL, params=params) as response:
            found = await response.json(content_type=None)
        if not found:
            raise PlaceNotFound(place)
        return (found[0].get("name") or place, (float(found[0]["lat"]), float(found[0]["lon"])))

    async def _overpass(self, session: aiohttp.ClientSession, query: str) -> list[dict]:
        tasks = [asyncio.create_task(self._ask(session, url, query)) for url in OVERPASS_MIRRORS]
        try:
            error = SourceUnavailable("зеркала Overpass не ответили")
            for finished in asyncio.as_completed(tasks):
                try:
                    return await finished
                except Exception as failure:
                    error = failure
            raise error
        finally:
            for task in tasks:
                task.cancel()

    async def _ask(self, session: aiohttp.ClientSession, url: str, query: str) -> list[dict]:
        async with session.post(url, data={"data": query}) as response:
            if response.status != 200:
                raise SourceUnavailable(f"Overpass ответил {response.status}")
            answer = await response.json(content_type=None)
        if not answer.get("elements") and answer.get("remark"):
            raise SourceUnavailable(answer["remark"])
        return answer.get("elements", [])


def _query(category: Category, center: tuple) -> str:
    lat, lon = center
    degrees_lat = RADIUS_KM / 111.0
    degrees_lon = RADIUS_KM / (111.0 * max(math.cos(math.radians(lat)), 0.1))
    scope = f"({lat - degrees_lat:.4f},{lon - degrees_lon:.4f},{lat + degrees_lat:.4f},{lon + degrees_lon:.4f})"
    tags = "".join(f'nwr["{key}"="{value}"]{scope};' for key, value in category.tags)
    return f"[out:json][timeout:{QUERY_TIMEOUT}];({tags});out center tags {RESULT_LIMIT};"


def _tag(tags: dict, *names: str) -> str:
    return next((tags[name] for name in names if tags.get(name)), "")


def _many(tags: dict, *names: str) -> list[str]:
    return [part.strip() for part in _tag(tags, *names).split(";") if part.strip()]


def _to_supplier(element: dict, place_name: str, source_title: str) -> Supplier | None:
    tags = element.get("tags") or {}
    name = _tag(tags, "name", "operator")
    if not name:
        return None
    website = _tag(tags, "website", "contact:website")
    kind_tag = _tag(tags, "shop", "craft", "industrial", "man_made", "office")
    osm_id = f"{element['type']}/{element['id']}"
    return Supplier(
        name=name,
        kind=KIND_TITLES.get(kind_tag, kind_tag or UNKNOWN_KIND),
        address=", ".join(
            filter(
                None,
                (
                    _tag(tags, "addr:city") or place_name,
                    _tag(tags, "addr:street"),
                    _tag(tags, "addr:housenumber"),
                ),
            )
        ),
        phones=_many(tags, "phone", "contact:phone"),
        emails=_many(tags, "email", "contact:email"),
        website=website if not website or website.startswith("http") else "https://" + website,
        hours=_tag(tags, "opening_hours"),
        wholesale=bool(
            _tag(tags, "wholesale", "craft", "industrial")
            or tags.get("shop") == "wholesale"
            or looks_wholesale(name)
        ),
        source=f"https://www.openstreetmap.org/{osm_id}",
        source_title=source_title,
    )
