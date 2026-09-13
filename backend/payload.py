import catalog

NO_SITE = "—"


def meta(stats: dict, state: dict, sources: list[dict]) -> dict:
    return {
        "categories": [{"id": catalog.ANY, "title": catalog.ANY_CATEGORY_TITLE}]
        + [{"id": item.id, "title": item.title} for item in catalog.CATEGORIES],
        "regions": [catalog.ANY_REGION_TITLE, *catalog.REGIONS],
        "cities": {
            catalog.ANY_REGION_TITLE: list(catalog.cities_of(catalog.ANY)),
            **{region: list(catalog.cities_of(region)) for region in catalog.REGIONS},
        },
        "sorts": list(catalog.SORTS),
        "defaults": {
            "category": catalog.ANY,
            "region": catalog.ANY_REGION_TITLE,
            "city": catalog.ANY_CITY_TITLE,
            "sort": catalog.SORTS[0],
        },
        "labels": {
            "anyCategory": catalog.ANY_CATEGORY_TITLE,
            "anyRegion": catalog.ANY_REGION_TITLE,
            "anyCity": catalog.ANY_CITY_TITLE,
        },
        "stats": stats,
        "status": status(state),
        "sources": sources,
    }


def status(state: dict) -> dict:
    return {
        "indexing": state["indexing"],
        "city": state["city"],
        "citiesDone": state["cities_done"],
        "citiesTotal": state["cities_total"],
        "enriching": state["enriching"],
        "enriched": state["enriched"],
    }


def page(rows: list[dict], total: int, page_number: int, per_page: int, notes: dict) -> dict:
    pages = max(1, -(-total // per_page))
    return {
        "items": [card(row, notes) for row in rows],
        "total": total,
        "page": page_number,
        "pages": pages,
        "perPage": per_page,
    }


def card(row: dict, notes: dict) -> dict:
    cats = [catalog.title(item) for item in row["cats"].split(",") if item]
    if row.get("kind") and row["kind"] not in cats:
        cats.append(row["kind"])
    return {
        "id": row["id"],
        "name": row["name"],
        "city": row["city"],
        "region": row["region"],
        "cats": cats,
        "kind": row.get("kind", ""),
        "rating": row.get("rating"),
        "reviews": row.get("reviews"),
        "sourcesCount": len(row.get("sources") or []),
        "moq": row.get("moq", ""),
        "moqValue": row.get("moq_value"),
        "price": row.get("price", ""),
        "delivery": row.get("delivery", ""),
        "geo": row.get("geo", ""),
        "years": row.get("years", ""),
        "verified": bool(row.get("verified")),
        "verifiedBy": row.get("verified_by", ""),
        "certs": row.get("certs") or [],
        "manager": row.get("manager", ""),
        "about": row.get("about", ""),
        "phone": (row.get("phones") or [""])[0],
        "email": (row.get("emails") or [""])[0],
        "site": _domain(row.get("website", "")),
        "phones": row.get("phones") or [],
        "emails": row.get("emails") or [],
        "address": row.get("address", ""),
        "hours": row.get("hours", ""),
        "wholesale": bool(row.get("wholesale")),
        "branches": row.get("branches", 1),
        "inn": row.get("inn", ""),
        "ogrn": row.get("ogrn", ""),
        "source": row.get("source", ""),
        "sourceTitle": row.get("source_title", ""),
        "sources": row.get("sources") or [],
        "score": row.get("score", 0),
        "level": row.get("level", "low"),
        "verdict": row.get("verdict", ""),
        "plus": row.get("plus") or [],
        "minus": row.get("minus") or [],
        "checkedAt": row.get("checked_at") or row.get("updated_at") or 0,
        "note": notes.get(row["id"], ""),
    }


def _domain(website: str) -> str:
    if not website:
        return NO_SITE
    host = website.split("//")[-1].rstrip("/")
    try:
        return host.encode("ascii").decode("idna")
    except (UnicodeError, ValueError):
        return host
