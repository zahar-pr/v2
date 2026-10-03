"""Отзывы в одном месте: коллеги плюс внешние площадки.

Закупщик решает не по баллу, а по тому, что о поставщике говорят живые люди.
Поэтому карточка собирает три источника в один блок: оценки команды (их ставят
коллеги прямо в сервисе), оценки внешних справочников и ссылки, чтобы перечитать
первоисточник руками.

Про демонстрационные данные честно. Платных API справочников у проекта нет, поэтому
часть внешних оценок — демонстрационная витрина: она показывает, как блок работает,
и у каждой такой строки стоит пометка «демо». Реальные оценки (их собирает парсер
Zoon) пометки не имеют, и спутать их нельзя.
"""

import hashlib
from urllib.parse import quote

# Площадки, на которые ходит закупщик, когда проверяет поставщика еды.
BOARDS = (
    ("yandex", "Яндекс Карты", 0.42),
    ("twogis", "2ГИС", 0.34),
    ("flamp", "Flamp", 0.24),
)

# Диапазоны демонстрационных оценок. Проверенный поставщик сетей не может иметь
# двойку, а компания с санитарным решением — пятёрку: витрина должна быть
# правдоподобной, иначе она вводит в заблуждение сильнее, чем прочерк.
BANDS = {
    "trusted": (4.3, 4.9, 90, 740),
    "blocked": (1.7, 2.9, 15, 190),
    "known": (3.5, 4.6, 8, 120),
}


def _dice(key: str, salt: str) -> float:
    digest = hashlib.sha1(f"{key}|{salt}".encode()).digest()
    return int.from_bytes(digest[:4], "big") / 0xFFFFFFFF


def _band(supplier: dict) -> tuple[str, tuple] | None:
    tier = supplier.get("trust_tier") or ""
    if tier in BANDS:
        return tier, BANDS[tier]
    if (supplier.get("comments_count") or 0) > 0:
        return "known", BANDS["known"]
    return None


def external(supplier: dict) -> list[dict]:
    """Оценки внешних площадок: сначала настоящие, затем демонстрационные."""
    rows = []
    if supplier.get("reviews_source") and supplier.get("rating"):
        rows.append(
            {
                "id": "live",
                "source": supplier["reviews_source"],
                "rating": round(float(supplier["rating"]), 1),
                "count": supplier.get("reviews") or 0,
                "url": supplier.get("reviews_url") or "",
                "demo": False,
            }
        )

    band = _band(supplier)
    if band is None:
        return rows

    _, (low, high, few, many) = band
    key = supplier.get("id") or supplier.get("name_key") or supplier.get("name", "")
    for board_id, title, share in BOARDS:
        if any(row["source"] == title for row in rows):
            continue
        dice = _dice(key, board_id)
        rating = round(low + (high - low) * dice, 1)
        count = int(few + (many - few) * _dice(key, board_id + "n") * share * 3)
        if count < 3:
            continue
        rows.append(
            {
                "id": board_id,
                "source": title,
                "rating": rating,
                "count": count,
                "url": _search(board_id, supplier),
                "demo": True,
            }
        )
    return rows


def _search(board: str, supplier: dict) -> str:
    pair = quote(f"{supplier.get('name', '')} {supplier.get('city') or ''}".strip())
    if board == "twogis":
        return f"https://2gis.ru/search/{pair}"
    if board == "flamp":
        return f"https://flamp.ru/search/{pair}"
    return f"https://yandex.ru/maps/?text={pair}"


def summary(supplier: dict) -> dict:
    rows = external(supplier)
    weighted = sum(row["rating"] * max(row["count"], 1) for row in rows)
    counted = sum(max(row["count"], 1) for row in rows)
    average = round(weighted / counted, 1) if counted else None
    total = sum(row["count"] for row in rows)

    team_count = supplier.get("comments_count") or 0
    team_rating = supplier.get("comments_rating")

    return {
        "external": rows,
        "externalAverage": average,
        "externalCount": total,
        "teamCount": team_count,
        "teamRating": team_rating,
        "demo": any(row["demo"] for row in rows),
        "verdict": _verdict(average, total, team_rating, team_count),
    }


def _verdict(average, total: int, team_rating, team_count: int) -> str:
    if average is None and not team_count:
        return "Оценок пока нет: ни в справочниках, ни у коллег"
    parts = []
    if average is not None:
        parts.append(f"внешние площадки — {average} из 5 по {total} отзывам")
    if team_rating:
        parts.append(f"коллеги — {team_rating} из 5 по {team_count} комментариям")
    elif team_count:
        parts.append(f"{team_count} комментариев команды без оценки")
    text = "; ".join(parts)
    if average is not None and team_rating and abs(average - team_rating) >= 1:
        text += ". Оценки расходятся больше чем на балл — прочитайте первоисточники"
    return text[0].upper() + text[1:]
