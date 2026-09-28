import os
import uuid
from dataclasses import dataclass, field

import catalog
import payload
import scoring
import store
import team
from fastapi import Depends, HTTPException, Query, Request, Response

COOKIE = "provizia_user"
COOKIE_AGE = 60 * 60 * 24 * 365
PER_PAGE = 12
MAX_PER_PAGE = 60
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "")

RELAX_LABELS = {
    "only_docs": "Без условия «с документами»",
    "only_verified": "Без условия «подтверждённые»",
    "only_contacts": "Вместе с теми, у кого нет контактов",
    "kinds": "Вместе с розницей",
    "query": "Без строки поиска",
    "category": "Все категории",
    "city": "Весь регион",
    "region": "Вся страна",
    "status": "Любой статус",
}


def user_id(request: Request, response: Response) -> str:
    found = request.cookies.get(COOKIE)
    if not found:
        found = uuid.uuid4().hex
        response.set_cookie(COOKIE, found, max_age=COOKIE_AGE, httponly=True, samesite="lax")
    return found


@dataclass
class Filters:
    query: str = ""
    category: str = ""
    region: str = ""
    city: str = ""
    kinds: tuple[str, ...] = ()
    only_docs: bool = False
    only_verified: bool = False
    only_contacts: bool = False
    status: str = ""
    preset: str = scoring.DEFAULT_PRESET
    weights: dict = field(default_factory=dict)
    sort: str = catalog.SORTS[0]

    def search(self, page: int = 1, per_page: int = PER_PAGE):
        return store.search(
            query=self.query,
            category=self.category,
            region=self.region,
            city=self.city,
            kinds=self.kinds,
            only_docs=self.only_docs,
            only_verified=self.only_verified,
            only_contacts=self.only_contacts,
            status=self.status,
            weights=self.weights,
            sort=self.sort,
            page=page,
            per_page=per_page,
        )

    def as_dict(self) -> dict:
        return {
            "query": self.query,
            "category": self.category,
            "region": self.region,
            "city": self.city,
            "kinds": self.kinds,
            "only_docs": self.only_docs,
            "only_verified": self.only_verified,
            "only_contacts": self.only_contacts,
            "status": self.status,
            "weights": self.weights,
        }


def filters(
    q: str = Query("", max_length=120),
    category: str = Query(catalog.ANY),
    region: str = Query(catalog.ANY_REGION_TITLE),
    city: str = Query(catalog.ANY_CITY_TITLE),
    kinds: str = Query(""),
    onlyDocs: bool = Query(False),
    onlyVerified: bool = Query(False),
    onlyContacts: bool = Query(False),
    status: str = Query(""),
    preset: str = Query(scoring.DEFAULT_PRESET),
    weights: str = Query(""),
    sort: str = Query(catalog.SORTS[0]),
) -> Filters:
    chosen_category = _categories(category)

    chosen_city = "" if city in ("", catalog.ANY, catalog.ANY_CITY_TITLE) else city
    if chosen_city and catalog.city(chosen_city) is None:
        raise HTTPException(404, f"Не знаю город «{chosen_city}»")

    return Filters(
        query=q,
        category=chosen_category,
        region="" if region in ("", catalog.ANY, catalog.ANY_REGION_TITLE) else region,
        city=chosen_city,
        kinds=kinds_of(kinds),
        only_docs=onlyDocs,
        only_verified=onlyVerified,
        only_contacts=onlyContacts,
        status=status,
        preset=preset,
        weights=weights_of(preset, weights),
        sort=sort,
    )


Query_ = Depends(filters)


def _categories(raw: str) -> str:
    chosen = [item for item in (raw or "").split(",") if item and item != catalog.ANY]
    unknown = [item for item in chosen if catalog.category(item) is None]
    if unknown:
        raise HTTPException(400, f"Неизвестная категория «{unknown[0]}»")
    return ",".join(chosen)


def weights_of(preset: str, raw: str) -> dict:
    custom: dict = {}
    for chunk in (raw or "").split(","):
        name, _, value = chunk.partition(":")
        if name.strip() and value.strip().isdigit():
            custom[name.strip()] = int(value)
    return scoring.weights_of(preset, custom)


def kinds_of(raw: str) -> tuple[str, ...]:
    known = {item["id"] for item in payload.KINDS}
    chosen = tuple(item for item in (raw or "").split(",") if item in known)
    return () if len(chosen) == len(known) else chosen


def notes() -> dict:
    return {
        item["supplier_id"]: {"text": item["text"], "author": item["author"]}
        for item in team.notes_of()
    }


def checks(rows: list[dict]) -> dict:
    return {row["id"]: team.checks_of(row["id"]) for row in rows}


def cards(rows: list[dict], weights: dict) -> list[dict]:
    saved_notes, statuses = notes(), team.statuses_of()
    return [
        payload.card(row, saved_notes, statuses, weights, rank=number + 1, checks=checks(rows))
        for number, row in enumerate(rows)
    ]


def by_score(rows: list[dict], weights: dict) -> list[dict]:
    """Карточки по убыванию приоритета: нумерация в списке обзвона должна совпадать с ним."""
    ranked = sorted(cards(rows, weights), key=lambda item: -item["score"])
    for number, item in enumerate(ranked, 1):
        item["rank"] = number
    return ranked


def require_admin(token: str) -> None:
    if not ADMIN_TOKEN or token != ADMIN_TOKEN:
        raise HTTPException(403, "Нужен ADMIN_TOKEN")


def recommendation(best: dict, runner: dict | None, chosen: list[dict]) -> str:
    text = f"Звонить первым — «{best['name']}»: {best['score']} из 100 по вашим приоритетам"
    strong = max(best["factors"], key=lambda item: item["score"] * max(item["weight"], 1))
    if strong["plus"]:
        text += f". Сильная сторона — {strong['title'].lower()}: {strong['plus'][0]}"
    if runner:
        gap = best["score"] - runner["score"]
        text += f". «{runner['name']}» отстаёт на {gap} {points_word(gap)}"
    if best["ask"][:2]:
        text += ". Что спросить в первом звонке: " + "; ".join(best["ask"][:2]).lower()
    missing = [item["name"] for item in chosen if not item["phone"] and not item["email"]]
    if missing:
        text += f". Без контактов в источниках: {', '.join(missing)}"
    return text + "."


def factor_diff(best: dict, runner: dict | None) -> list[dict]:
    if runner is None:
        return []

    rows = []
    for position, (first, second) in enumerate(zip(best["factors"], runner["factors"])):
        gap = first["score"] - second["score"]
        if gap == 0:
            continue
        leader, behind = (best, runner) if gap > 0 else (runner, best)
        rows.append(
            {
                "factor": first["title"],
                "leader": leader["name"],
                "gap": abs(gap),
                "weight": first["weight"],
                "reason": (leader["factors"][position]["plus"] or [""])[0],
                "lack": (behind["factors"][position]["minus"] or [""])[0],
            }
        )
    return sorted(rows, key=lambda item: -item["gap"] * max(item["weight"], 1))[:4]


def points_word(n: int) -> str:
    return _plural(n, "пункт", "пункта", "пунктов")


def _plural(n: int, one: str, few: str, many: str) -> str:
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not 10 <= n % 100 < 20:
        return few
    return many
