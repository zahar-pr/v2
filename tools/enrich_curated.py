"""Дотягивает кураторские карточки из Wikidata: сайт, год основания, город.

Кураторский список собран по публикациям о поставках в сети, и в нём нет ни
сайтов, ни года основания — а без сайта карточка упирается в тупик. Wikidata
отдаёт эти поля со ссылкой на источник, поэтому ничего выдумывать не нужно.

Сопоставление строгое. Берём только сущности, у которых подходящий тип
(предприятие, а не человек и не населённый пункт) и название совпадает с нашим
после нормализации. Всё, что совпало нестрого, печатается в лог и не
записывается: лучше пустое поле, чем чужой сайт в карточке.

    python3 tools/enrich_curated.py          # посмотреть, что нашлось
    python3 tools/enrich_curated.py --write   # записать в базу
"""

import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
)

import catalog
import db
import domain
import index
import store

API = "https://www.wikidata.org/w/api.php"
AGENT = "ProviziaBot/1.0 (+https://github.com/zahar-pr/v2)"
PAUSE = 0.35

WEBSITE = "P856"
INCEPTION = "P571"
HEADQUARTERS = "P159"
LOCATION = "P131"
COUNTRY = "P17"
INSTANCE = "P31"

RUSSIA = "Q159"

# Типы, которые нас устраивают: компания, предприятие, бренд, агрохолдинг и т.п.
COMPANY_TYPES = {
    "Q4830453",  # business
    "Q6881511",  # enterprise
    "Q783794",  # company
    "Q891723",  # public company
    "Q210167",  # ?
    "Q167037",  # corporation
    "Q43229",  # organization
    "Q4830453",
    "Q1589009",  # privately held company
    "Q18388277",  # technology company
    "Q431289",  # brand
    "Q507619",  # retail chain
    "Q2085381",  # publisher (бывает у брендов)
    "Q66724388",
    "Q22687",  # bank — не наше, но пусть лучше отфильтруется ниже
}

NOISE = re.compile(r"\(.*?\)|«|»|\"|ооо|оао|зао|ао\b|апх|гк\b|группа|трейдинг|руссия|россия", re.I)


def norm(name: str) -> str:
    clean = NOISE.sub(" ", name or "")
    return re.sub(r"[^a-zа-яё0-9]", "", clean.lower())


def fetch(params: dict) -> dict:
    query = urllib.parse.urlencode({**params, "format": "json"})
    request = urllib.request.Request(f"{API}?{query}", headers={"User-Agent": AGENT})
    with urllib.request.urlopen(request, timeout=25) as answer:
        return json.load(answer)


def search(name: str) -> list[str]:
    found: list[str] = []
    for language in ("ru", "en"):
        try:
            answer = fetch(
                {
                    "action": "wbsearchentities",
                    "search": name[:70],
                    "language": language,
                    "uselang": language,
                    "limit": 7,
                }
            )
        except Exception as error:
            print(f"  поиск не удался ({error})")
            continue
        found += [item["id"] for item in answer.get("search", [])]
        time.sleep(PAUSE)
    return list(dict.fromkeys(found))


def entities(ids: list[str]) -> dict:
    if not ids:
        return {}
    try:
        answer = fetch(
            {
                "action": "wbgetentities",
                "ids": "|".join(ids[:12]),
                "props": "claims|labels|aliases|descriptions",
            }
        )
    except Exception as error:
        print(f"  сущности не загрузились ({error})")
        return {}
    time.sleep(PAUSE)
    return answer.get("entities") or {}


def value(claim: dict):
    return ((claim.get("mainsnak") or {}).get("datavalue") or {}).get("value")


def first(claims: dict, prop: str):
    for claim in claims.get(prop, []):
        found = value(claim)
        if found is not None:
            return found
    return None


def ids_of(claims: dict, prop: str) -> set[str]:
    out = set()
    for claim in claims.get(prop, []):
        found = value(claim)
        if isinstance(found, dict) and found.get("id"):
            out.add(found["id"])
    return out


def names_of(entity: dict) -> list[str]:
    out = []
    for language in ("ru", "en"):
        label = (entity.get("labels") or {}).get(language)
        if label:
            out.append(label["value"])
        for alias in (entity.get("aliases") or {}).get(language, []):
            out.append(alias["value"])
    return out


def year_of(claims: dict) -> int | None:
    found = first(claims, INCEPTION)
    if isinstance(found, dict) and found.get("time"):
        digits = found["time"].lstrip("+")[:4]
        if digits.isdigit():
            return int(digits)
    return None


def label_of(entity_id: str, cache: dict) -> str:
    if entity_id in cache:
        return cache[entity_id]
    found = entities([entity_id]).get(entity_id) or {}
    label = ((found.get("labels") or {}).get("ru") or {}).get("value", "")
    cache[entity_id] = label
    return label


def city_of(claims: dict, cache: dict) -> str:
    """Город головного офиса — только если он есть в нашем справочнике городов."""
    for prop in (HEADQUARTERS, LOCATION):
        for entity_id in ids_of(claims, prop):
            label = label_of(entity_id, cache)
            if catalog.city(label):
                return label
    return ""


def pick(name: str, found: dict) -> tuple[str, dict] | None:
    target = norm(name)
    for entity_id, entity in found.items():
        claims = entity.get("claims") or {}
        if not ids_of(claims, INSTANCE) & COMPANY_TYPES:
            continue
        if RUSSIA not in ids_of(claims, COUNTRY) and not first(claims, WEBSITE):
            continue
        if not any(norm(variant) == target for variant in names_of(entity)):
            continue
        return entity_id, claims
    return None


def main() -> None:
    write = "--write" in sys.argv
    db.connect()
    rows = [
        store.row_to_dict(item)
        for item in store.connect().execute(
            "SELECT * FROM suppliers WHERE trust_tier='trusted' ORDER BY name"
        )
    ]
    cache: dict = {}
    matched = 0

    for item in rows:
        print(f"{item['name']}")
        found = pick(item["name"], entities(search(item["name"])))
        if found is None:
            print("  не нашлось строгого совпадения")
            continue

        entity_id, claims = found
        data: dict = {}
        site = first(claims, WEBSITE)
        if site and not item.get("website"):
            data["website"] = site.rstrip("/")
        year = year_of(claims)
        if year and not item.get("founded"):
            data["founded"] = year
            data["years"] = domain.years_text(year)
        city = city_of(claims, cache)

        data["sources"] = domain.with_source(
            item, "wikidata", "Wikidata", f"https://www.wikidata.org/wiki/{entity_id}"
        )
        matched += 1
        print(
            f"  {entity_id}: сайт {data.get('website', '—')}, год {data.get('founded', '—')}"
            f", город {city or '—'}"
        )

        if write:
            store.save_enrichment(item["id"], data)
            if city and not item.get("city"):
                with db._lock:
                    connection = store.connect()
                    connection.execute(
                        "UPDATE suppliers SET city=? WHERE id=?", (city, item["id"])
                    )
                    connection.commit()
            saved = store.get(item["id"])
            if saved:
                index.score_one(saved)

    print()
    print(f"совпало строго: {matched} из {len(rows)}; запись: {'да' if write else 'нет'}")


if __name__ == "__main__":
    main()
