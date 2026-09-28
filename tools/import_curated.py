"""Заносит в базу два кураторских списка.

`suppliers_top_chains.json` — поставщики топовых сетей общепита. Им проставляется
`trust_tier = trusted`: максимальный балл и зелёная карточка.

`suppliers_goulash.json` — компании, которым Роспотребнадзор приостанавливал работу.
Им проставляется `trust_tier = blocked`: нулевой балл и красная карточка.

Тексты «почему» собираются из полей самого файла. Если в нём написано, что связь с
сетью не подтверждена или historическая, в карточке будет написано ровно это —
выдумывать сотрудничество нельзя.

    python3 tools/import_curated.py <top_chains.json> <goulash.json>
"""

import json
import os
import re
import sys
import time

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
)

import catalog
import domain
import index
import store
from db import connect

CATEGORY_WORDS = (
    ("meat", ("мясо", "курица", "птиц", "говядин", "свинин", "колбас", "бекон", "котлет")),
    ("fish", ("рыб", "морепродукт", "лосос", "минтай", "креветк", "краб")),
    ("dairy", ("молоч", "молок", "сыр", "сливк", "творог", "масло сливоч")),
    ("bakery", ("хлеб", "булоч", "выпечк", "пекарн")),
    ("confectionery", ("десерт", "торт", "чизкейк", "конditer", "кондитер", "тирамису")),
    ("grain", ("мука", "круп", "рис", "макарон", "паста", "зерно")),
    ("vegetables", ("овощ", "салат", "картофел", "томат", "фрукт", "зелен", "лук")),
    ("drinks", ("напит", "кофе", "чай", "сок", "вода", "лимонад", "газиров")),
    ("frozen", ("заморозк", "фри", "полуфабрикат", "хашбраун", "драник")),
    ("spices", ("соус", "кетчуп", "майонез", "вкусоаромат", "специи", "васаби", "имбирь")),
    ("packaging", ("упаковк", "стакан", "тар")),
    ("wholesale", ("дистрибуц", "логистик", "кэш-энд-кэрри", "оборудование", "по/", "пос")),
)

LINK_TEXT = {
    "актуально": "Сотрудничество подтверждено публикациями",
    "историческое (до 2022)": "Сотрудничество подтверждалось до 2022 года",
    "не подтверждено публично": "Крупный федеральный игрок HoReCa; связь с конкретной сетью публично не подтверждена",
}


def slug(name: str) -> str:
    key = re.sub(r"[^a-zа-я0-9]+", "-", name.lower()).strip("-")
    return key[:60]


def category_of(text: str) -> str:
    found = [key for key, words in CATEGORY_WORDS if any(w in text.lower() for w in words)]
    return "," + ",".join(found or ["wholesale"]) + ","


def city_of(raw: str) -> tuple[str, str]:
    """Возвращает (город из каталога, регион как написано в файле)."""
    place = (raw or "").split("(")[0].split(",")[0].strip()
    known = catalog.city(place)
    return (known.name if known else "", place)


def trusted_note(item: dict) -> str:
    clients = item.get("known_clients") or []
    status = item.get("client_link_status") or ""
    lines = []
    if clients:
        lines.append("Поставляет для: " + ", ".join(clients) + ".")
    lines.append(LINK_TEXT.get(status, status).rstrip(".") + ".")
    products = item.get("products") or []
    if products:
        lines.append("Что возит: " + ", ".join(products) + ".")
    regions = [r for r in (item.get("regions") or []) if r and r != "—"]
    if regions:
        lines.append("География: " + ", ".join(regions) + ".")
    if item.get("note"):
        lines.append(item["note"].rstrip(".") + ".")
    return " ".join(lines)


def blocked_note(item: dict) -> str:
    lines = [item.get("notes", "").rstrip(".") + "."]
    if item.get("sanction"):
        lines.insert(0, f"{item['sanction']} ({item.get('date', 'дата не указана')}).")
    if item.get("client_chain"):
        status = (item.get("relation_status") or "").lower()
        mark = " (бывший)" if status == "бывший" else ""
        lines.append(f"Поставлял в сеть «{item['client_chain']}»{mark}.")
    if item.get("products"):
        lines.append("Продукция: " + item["products"] + ".")
    return " ".join(line for line in lines if line.strip(". "))


def record(name: str, item: dict, tier: str, note: str, cats: str) -> dict:
    city, area = city_of(item.get("city") or (item.get("regions") or [""])[0])
    return {
        "id": f"curated:{tier}:{slug(name)}",
        "name": name,
        "name_key": domain.name_key(name),
        "city": city,
        "region": catalog.city(city).region if city else catalog.region_by_area(area),
        "area": area,
        "cats": cats,
        "kind": item.get("category") or item.get("products") or "",
        "kind_tag": "",
        # не розница: иначе карточка с санкциями спрячется под фильтром типа
        "kind_class": "producer",
        "address": "",
        "phones": [],
        "emails": [],
        "socials": [],
        "website": "",
        "hours": "",
        "wholesale": 1,
        "branches": 1,
        "lat": None,
        "lon": None,
        "source": (item.get("sources") or [""])[0],
        "source_title": "Кураторский список",
        "sources": [
            {"id": f"curated-{number}", "title": _source_title(url), "url": url}
            for number, url in enumerate(item.get("sources") or [], 1)
        ],
        "haystack": " ".join([name, note, item.get("category", ""), area]).lower(),
        "distance_km": None,
        "checked_at": time.time(),
    }


def _source_title(url: str) -> str:
    host = re.sub(r"^https?://(www\.)?", "", url).split("/")[0]
    return host or "Источник"


def load_trusted(path: str) -> list[tuple[dict, dict]]:
    data = json.loads(open(path, encoding="utf-8").read())
    out = []
    for item in data["suppliers"]:
        name = item["name"]
        note = trusted_note(item)
        cats = category_of(f"{item.get('category', '')} {' '.join(item.get('products') or [])}")
        row = record(name, item, "trusted", note, cats)
        extra = {
            "about": note,
            "trust_tier": "trusted",
            "trust_note": note,
            "clients": item.get("known_clients") or [],
            "products": item.get("products") or [],
            "geo": ", ".join(r for r in (item.get("regions") or []) if r and r != "—"),
            "sources": row["sources"],
        }
        out.append((row, extra))
    return out


def load_blocked(path: str) -> list[tuple[dict, dict]]:
    data = json.loads(open(path, encoding="utf-8").read())
    merged: dict[str, dict] = {}
    for item in data["suppliers"]:
        key = domain.name_key(item["supplier"])
        merged.setdefault(key, item)
        if len(item.get("notes", "")) > len(merged[key].get("notes", "")):
            merged[key] = item

    out = []
    for item in merged.values():
        name = (
            f"{item['supplier']} ({item['legal_form']})"
            if item.get("legal_form") not in ("", "н/д")
            else item["supplier"]
        )
        note = blocked_note(item)
        row = record(name, item, "blocked", note, category_of(item.get("products", "")))
        extra = {
            "about": note,
            "trust_tier": "blocked",
            "trust_note": note,
            "incident": {
                "risk": item.get("risk", ""),
                "date": item.get("date", ""),
                "sanction": item.get("sanction", ""),
                "chain": item.get("client_chain", ""),
                "status": item.get("relation_status", ""),
                "notes": item.get("notes", ""),
            },
            "sources": row["sources"],
        }
        out.append((row, extra))
    return out


def mark_existing(rows: list[tuple[dict, dict]]) -> int:
    """Метит уже имеющиеся в индексе карточки той же компании.

    Делается только для санкций: об опасном поставщике надо предупредить везде, где он
    встречается. Зелёные так не метим — у бренда в индексе бывает десяток филиалов и
    магазинов, и выдача превратилась бы в стену из одинаковых названий. Проверенного
    поставщика представляет одна кураторская карточка.
    """
    connection = connect()
    touched = 0
    for row, extra in rows:
        found = connection.execute(
            "SELECT id FROM suppliers WHERE name_key = ? AND id != ?",
            (row["name_key"], row["id"]),
        ).fetchall()
        for item in found:
            store.save_enrichment(item["id"], extra)
            touched += 1
    return touched


def main() -> None:
    top, bad = sys.argv[1], sys.argv[2]
    batches = [("сетевые", load_trusted(top)), ("неблагонадёжные", load_blocked(bad))]

    for title, rows in batches:
        store.save_indexed([row for row, _ in rows])
        for row, extra in rows:
            store.save_enrichment(row["id"], extra)
        also = mark_existing(rows) if title == "неблагонадёжные" else 0
        print(f"{title}: занесено {len(rows)}, помечено уже бывших в базе {also}")

    for _, rows in batches:
        for row, _ in rows:
            fresh = store.get(row["id"])
            if fresh:
                index.score_one(fresh)
    print("баллы пересчитаны")


if __name__ == "__main__":
    main()
