import csv
import io
import time
from urllib.parse import quote

import catalog
import domain
import scoring

NO_SITE = "—"
KIND_LIMIT = 34
STATUSES = (
    {"id": "new", "title": "Новый"},
    {"id": "calling", "title": "В работе"},
    {"id": "quoted", "title": "Запросили КП"},
    {"id": "fit", "title": "Подходит"},
    {"id": "rejected", "title": "Отказ"},
)
KINDS = (
    {"id": "producer", "title": "Производство"},
    {"id": "wholesale", "title": "Оптовая база"},
    {"id": "retail", "title": "Розничная точка"},
    {"id": "unknown", "title": "Не определён"},
)
SUPPLY_KINDS = ("producer", "wholesale", "unknown")


def meta(stats: dict, state: dict, sources: list[dict], defaults: dict | None = None) -> dict:
    defaults = defaults or {}
    return {
        "categories": [{"id": catalog.ANY, "title": catalog.ANY_CATEGORY_TITLE}]
        + [{"id": item.id, "title": item.title} for item in catalog.CATEGORIES],
        "regions": [catalog.ANY_REGION_TITLE, *catalog.REGIONS],
        "cities": {
            catalog.ANY_REGION_TITLE: list(catalog.cities_of(catalog.ANY)),
            **{region: list(catalog.cities_of(region)) for region in catalog.REGIONS},
        },
        "sorts": list(catalog.SORTS),
        "kinds": list(KINDS),
        "supplyKinds": list(SUPPLY_KINDS),
        "statuses": list(STATUSES),
        "factors": [
            {"id": factor.id, "title": factor.title, "hint": factor.hint}
            for factor in scoring.FACTORS
        ],
        "presets": [
            {
                "id": key,
                "title": preset["title"],
                "hint": preset["hint"],
                "weights": preset["weights"],
            }
            for key, preset in scoring.PRESETS.items()
        ],
        "defaults": {
            "category": defaults.get("category") or catalog.ANY,
            "region": defaults.get("region") or catalog.ANY_REGION_TITLE,
            "city": catalog.ANY_CITY_TITLE,
            "sort": catalog.SORTS[0],
            "preset": scoring.DEFAULT_PRESET,
            "kinds": list(SUPPLY_KINDS),
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
        "egrul": state.get("egrul", 0),
        "fns": state.get("fns", 0),
        "found": state.get("found", 0),
    }


def page(
    rows: list[dict],
    total: int,
    page_number: int,
    per_page: int,
    notes: dict,
    statuses: dict,
    weights: dict,
    preset: str,
    checks: dict | None = None,
) -> dict:
    pages = max(1, -(-total // per_page))
    start = (page_number - 1) * per_page
    return {
        "items": [
            card(row, notes, statuses, weights, rank=start + number + 1, checks=checks or {})
            for number, row in enumerate(rows)
        ],
        "total": total,
        "page": page_number,
        "pages": pages,
        "perPage": per_page,
        "weights": weights,
        "preset": preset,
    }


def card(
    row: dict,
    notes: dict,
    statuses: dict,
    weights: dict,
    rank: int = 0,
    checks: dict | None = None,
) -> dict:
    factors = scoring.evaluate(scoring.with_age(row))
    score = scoring.total(factors, weights)
    level, verdict = scoring.verdict_of(score)

    return {
        "id": row["id"],
        "rank": rank,
        "score": score,
        "level": level,
        "verdict": verdict,
        "factors": _factors(factors, weights),
        "ask": [question for factor in scoring.FACTORS for question in factors[factor.id]["ask"]],
        **_about(row),
        **_commerce(row),
        **_legal(row),
        **_contacts(row),
        **_trust(row),
        **_team(row, notes, statuses, checks or {}),
    }


def _factors(factors: dict, weights: dict) -> list[dict]:
    return [
        {
            "id": factor.id,
            "title": factor.title,
            "hint": factor.hint,
            "score": factors[factor.id]["score"],
            "weight": weights.get(factor.id, 0),
            "plus": factors[factor.id]["plus"],
            "minus": factors[factor.id]["minus"],
            "ask": factors[factor.id]["ask"],
        }
        for factor in scoring.FACTORS
    ]


def _about(row: dict) -> dict:
    cats = [catalog.title(item) for item in row["cats"].split(",") if item]
    kind = row.get("kind", "")
    if kind and kind != catalog.UNKNOWN_KIND and kind not in cats and len(kind) <= KIND_LIMIT:
        cats.append(kind)

    kind_class = row.get("kind_class") or "unknown"
    return {
        "name": row["name"],
        "city": row["city"],
        "area": row.get("area", ""),
        "region": row["region"],
        "cats": cats,
        "kind": kind,
        "type": kind_class,
        "typeTitle": domain.type_title(kind_class),
        "about": row.get("about", ""),
        "address": row.get("address", ""),
        "distanceKm": row.get("distance_km"),
        "branches": row.get("branches", 1),
    }


def _commerce(row: dict) -> dict:
    return {
        "moq": row.get("moq", ""),
        "moqValue": row.get("moq_value"),
        "price": row.get("price", ""),
        "priceList": row.get("price_list", ""),
        "delivery": row.get("delivery", ""),
        "ownDelivery": bool(row.get("own_delivery")),
        "geo": row.get("geo", ""),
        "hours": row.get("hours", ""),
        "wholesale": bool(row.get("wholesale")),
        "certs": row.get("certs") or [],
    }


def _legal(row: dict) -> dict:
    return {
        "inn": row.get("inn", ""),
        "ogrn": row.get("ogrn", ""),
        "okved": row.get("okved", ""),
        "okvedName": row.get("okved_name", ""),
        "legalName": row.get("legal_name", ""),
        "legalHead": row.get("manager", ""),
        "legalStatus": row.get("legal_status", ""),
        "legalActive": bool(row.get("legal_active")),
        "legalClosed": not bool(row.get("legal_active")) and bool(row.get("legal_status")),
        "years": row.get("years", ""),
        "founded": row.get("founded"),
        "manager": row.get("manager", ""),
    }


def _contacts(row: dict) -> dict:
    return {
        "phone": (row.get("phones") or [""])[0],
        "email": (row.get("emails") or [""])[0],
        "site": _domain(row.get("website", "")),
        "phones": row.get("phones") or [],
        "emails": row.get("emails") or [],
        "socials": row.get("socials") or [],
        "checkLinks": _check_links(row),
    }


def _trust(row: dict) -> dict:
    return {
        "rating": row.get("rating"),
        "reviews": row.get("reviews"),
        "reviewsUrl": row.get("reviews_url", ""),
        "reviewsSource": row.get("reviews_source", ""),
        "reviewLinks": _review_links(row),
        "verified": bool(row.get("verified")),
        "verifiedBy": row.get("verified_by", ""),
        "sourcesCount": len(row.get("sources") or []),
        "sources": row.get("sources") or [],
        "source": row.get("source", ""),
        "sourceTitle": row.get("source_title", ""),
        "checkedAt": row.get("checked_at") or row.get("updated_at") or 0,
    }


def _team(row: dict, notes: dict, statuses: dict, checks: dict) -> dict:
    note = notes.get(row["id"]) or {}
    status = statuses.get(row["id"]) or {}
    return {
        "note": note.get("text", ""),
        "noteAuthor": note.get("author", ""),
        "status": status.get("status", "new"),
        "statusAuthor": status.get("author", ""),
        "statusDays": _days_since(status.get("updated_at")),
        "checksDone": checks.get(row["id"], []),
        "commentsCount": row.get("comments_count", 0) or 0,
        "commentsRating": row.get("comments_rating"),
    }


def _days_since(moment) -> int | None:
    if not moment:
        return None
    return max(0, int((time.time() - moment) // 86400))


def _review_links(row: dict) -> list[dict]:
    name = row.get("name", "")
    where = row.get("city") or row.get("area") or ""
    pair = quote(f"{name} {where}".strip())
    return [
        {"title": "Отзывы в Яндексе", "url": f"https://yandex.ru/search/?text={pair}%20отзывы"},
        {"title": "Отзывы в 2ГИС", "url": f"https://2gis.ru/search/{pair}"},
        {"title": "Отзывы на Flamp", "url": f"https://flamp.ru/search/{pair}"},
    ]


def _check_links(row: dict) -> list[dict]:
    name = row.get("name", "")
    city = row.get("city") or row.get("area") or ""
    pair = quote(f"{name} {city}".strip())
    links = [
        {"title": "Найти в Яндексе", "url": f"https://yandex.ru/search/?text={pair}%20телефон"},
        {"title": "Найти в 2ГИС", "url": f"https://2gis.ru/search/{pair}"},
    ]
    query = row.get("inn") or name
    if query:
        links.append(
            {
                "title": "Проверить в ЕГРЮЛ",
                "url": f"https://egrul.nalog.ru/index.html?query={quote(query)}",
            }
        )
    return links


def _domain(website: str) -> str:
    if not website:
        return NO_SITE
    host = website.split("//")[-1].rstrip("/")
    try:
        return host.encode("ascii").decode("idna")
    except (UnicodeError, ValueError):
        return host


EXPORT_COLUMNS = (
    ("Приоритет", lambda c: c["score"]),
    ("Вердикт", lambda c: c["verdict"]),
    ("Название", lambda c: c["name"]),
    ("Тип", lambda c: c["typeTitle"]),
    ("Категории", lambda c: ", ".join(c["cats"])),
    ("Город", lambda c: c["city"]),
    ("Расстояние, км", lambda c: c["distanceKm"] if c["distanceKm"] is not None else ""),
    ("Телефон", lambda c: "; ".join(c["phones"])),
    ("Почта", lambda c: "; ".join(c["emails"])),
    ("Сайт", lambda c: c["site"] if c["site"] != NO_SITE else ""),
    ("Минимальный заказ", lambda c: c["moq"]),
    ("Цена", lambda c: c["price"]),
    ("Доставка", lambda c: c["delivery"]),
    ("Документы", lambda c: ", ".join(c["certs"])),
    ("Юрлицо", lambda c: c["legalName"]),
    ("Статус в ФНС", lambda c: c["legalStatus"]),
    ("ОКВЭД", lambda c: f'{c["okved"]} {c["okvedName"]}'.strip()),
    ("На рынке", lambda c: c["years"]),
    ("Руководитель", lambda c: c["legalHead"]),
    ("ИНН", lambda c: c["inn"]),
    ("ОГРН", lambda c: c["ogrn"]),
    ("Статус", lambda c: _status_title(c["status"])),
    ("Заметка", lambda c: c["note"]),
    ("Оценка команды", lambda c: f'{c["commentsRating"]} из 5' if c["commentsRating"] else ""),
    ("Комментариев", lambda c: c["commentsCount"] or ""),
    ("Что уточнить", lambda c: "; ".join(c["ask"])),
    ("Источник", lambda c: c["source"]),
)


def _status_title(status: str) -> str:
    return next((item["title"] for item in STATUSES if item["id"] == status), status)


def to_csv(cards: list[dict]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";", quoting=csv.QUOTE_MINIMAL)
    writer.writerow([title for title, _ in EXPORT_COLUMNS])
    for card_data in cards:
        writer.writerow([getter(card_data) for _, getter in EXPORT_COLUMNS])
    return buffer.getvalue()


def comment(row: dict, owner: str) -> dict:
    return {
        "id": row["id"],
        "author": row.get("author") or "Без имени",
        "text": row["text"],
        "rating": row.get("rating"),
        "createdAt": row.get("created_at") or 0,
        "mine": row.get("user_id") == owner,
    }
