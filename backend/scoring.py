import time
from dataclasses import dataclass

import domain

NEAR_KM = 10
CITY_KM = 25
REGION_KM = 60
FRESH_DAYS = 30
LOW_MOQ_KG = 200


@dataclass(frozen=True)
class Factor:
    id: str
    title: str
    hint: str


FACTORS = (
    Factor("reputation", "Репутация компании", "Что о компании говорят реестры и отзывы"),
    Factor("reach", "Связь", "Как быстро вы дозвонитесь и кому писать"),
    Factor("volume", "Опт и объёмы", "Работает ли с оптом и известны ли условия"),
    Factor("docs", "Документы", "Пройдёт ли проверку службы качества"),
    Factor("logistics", "Логистика", "Довезёт ли до вашего города"),
    Factor("trust", "Достоверность данных", "Насколько полны и свежи сами данные"),
)

PRESETS = {
    "balanced": {
        "title": "Сбалансированно",
        "hint": "Ровный вес всех факторов",
        "weights": {
            "reputation": 20,
            "reach": 20,
            "volume": 20,
            "docs": 15,
            "logistics": 15,
            "trust": 10,
        },
    },
    "trusted": {
        "title": "Проверенные компании",
        "hint": "Вперёд выходят те, у кого есть отзывы, история и чистый статус",
        "weights": {
            "reputation": 45,
            "reach": 10,
            "volume": 5,
            "docs": 20,
            "logistics": 5,
            "trust": 15,
        },
    },
    "urgent": {
        "title": "Дозвониться сегодня",
        "hint": "Вперёд выходят те, у кого есть телефон и часы работы",
        "weights": {
            "reputation": 10,
            "reach": 40,
            "volume": 15,
            "docs": 5,
            "logistics": 20,
            "trust": 10,
        },
    },
    "docs": {
        "title": "Нужны документы",
        "hint": "Вперёд выходят с декларациями и реквизитами",
        "weights": {
            "reputation": 25,
            "reach": 10,
            "volume": 10,
            "docs": 40,
            "logistics": 5,
            "trust": 10,
        },
    },
    "volume": {
        "title": "Нужен опт",
        "hint": "Вперёд выходят производства и оптовые базы",
        "weights": {
            "reputation": 20,
            "reach": 15,
            "volume": 40,
            "docs": 10,
            "logistics": 10,
            "trust": 5,
        },
    },
    "near": {
        "title": "Ближе к городу",
        "hint": "Вперёд выходят те, кто рядом и возит сам",
        "weights": {
            "reputation": 15,
            "reach": 20,
            "volume": 10,
            "docs": 5,
            "logistics": 45,
            "trust": 5,
        },
    },
}
DEFAULT_PRESET = "balanced"

VERDICTS = (
    (60, "high", "Звонить первым"),
    (35, "mid", "Хороший кандидат"),
    (18, "low", "Проверить вручную"),
    (0, "none", "Мало данных"),
)


def weights_of(preset: str, custom: dict | None = None) -> dict:
    if custom:
        clean = {f.id: max(0, min(100, int(custom.get(f.id, 0)))) for f in FACTORS}
        if sum(clean.values()) > 0:
            return clean
    return dict(PRESETS.get(preset, PRESETS[DEFAULT_PRESET])["weights"])


def with_age(row: dict) -> dict:
    data = dict(row)
    if row.get("checked_at"):
        data["checked_days_ago"] = (time.time() - row["checked_at"]) / 86400
    return data


def evaluate(supplier: dict) -> dict:
    return {
        "reputation": _reputation(supplier),
        "reach": _reach(supplier),
        "volume": _volume(supplier),
        "docs": _docs(supplier),
        "logistics": _logistics(supplier),
        "trust": _trust(supplier),
    }


def total(scores: dict, weights: dict) -> int:
    weight_sum = sum(weights.values()) or 1
    points = sum(scores[factor.id]["score"] * weights.get(factor.id, 0) for factor in FACTORS)
    return round(points / weight_sum)


def verdict_of(score: int) -> tuple[str, str]:
    level, text = next((level, text) for limit, level, text in VERDICTS if score >= limit)
    return level, text


def _box(points: int, plus: list, minus: list, ask: list) -> dict:
    return {
        "score": max(0, min(100, points)),
        "plus": plus,
        "minus": minus,
        "ask": ask,
    }


def _reputation(s: dict) -> dict:
    points, plus, minus, ask = 0, [], [], []

    rating = s.get("rating") if s.get("reviews_source") else None
    reviews = s.get("reviews")
    if rating:
        where = s.get("reviews_source") or "справочник"
        counted = f" по {reviews} отзывам" if reviews else ""
        if rating >= 4.5:
            points += 25
            plus.append(f"оценка {rating} из 5 на {where}{counted}")
        elif rating >= 4:
            points += 20
            plus.append(f"оценка {rating} из 5 на {where}{counted}")
        elif rating >= 3.5:
            points += 12
            plus.append(f"средняя оценка {rating} из 5 на {where}{counted}")
        else:
            minus.append(f"низкая оценка {rating} из 5 на {where}{counted}")
            ask.append("Прочитать отзывы: оценка ниже тройки")
    else:
        minus.append("оценок в справочниках отзывов не нашлось")
        ask.append("Посмотреть отзывы по ссылкам в карточке")

    team = s.get("comments_count") or 0
    team_rating = s.get("comments_rating")
    if team_rating:
        word = domain.plural(team, "комментарий", "комментария", "комментариев")
        plus.append(f"коллеги оценили на {team_rating} из 5 ({team} {word})")
        if team_rating >= 4:
            points += 25
        elif team_rating >= 3:
            points += 15
        else:
            minus.append(f"низкая оценка команды: {team_rating} из 5")
    elif team:
        points += 8
        word = domain.plural(team, "комментарий", "комментария", "комментариев")
        plus.append(f"{team} {word} от команды")
    else:
        minus.append("команда ещё не оставляла комментариев")
        ask.append("Записать вывод в комментарий после звонка")

    status = s.get("legal_status") or ""
    if s.get("legal_active"):
        points += 20
        plus.append(status.lower() if status else "действующее юрлицо по данным ФНС")
    elif status:
        minus.append(f"статус в ФНС: {status.lower()}")
        ask.append("Проверить, действует ли юрлицо")
    else:
        minus.append("юрлицо не найдено в реестрах ФНС")

    founded = s.get("founded")
    if founded:
        age = max(0, domain.CURRENT_YEAR - int(founded))
        if age >= 10:
            points += 20
        elif age >= 5:
            points += 15
        elif age >= 2:
            points += 8
        if age >= 2:
            plus.append(f"на рынке {age} {domain.plural(age, 'год', 'года', 'лет')}")
        else:
            minus.append("компания зарегистрирована меньше двух лет назад")
    else:
        minus.append("дата регистрации неизвестна")

    okved = s.get("okved") or ""
    if okved:
        points += 10
        name = (s.get("okved_name") or "").strip()
        plus.append(f"ОКВЭД {okved}: {name[:70]}" if name else f"ОКВЭД {okved}")

    return _box(points, plus, minus, ask)


def _reach(s: dict) -> dict:
    points, plus, minus, ask = 0, [], [], []
    phones = s.get("phones") or []
    if phones:
        points += 45
        plus.append(
            f"телефон: {phones[0]}"
            if len(phones) == 1
            else f"{len(phones)} {domain.plural(len(phones), 'телефон', 'телефона', 'телефонов')}"
        )
        if len(phones) > 1:
            points += 5
    else:
        minus.append("телефона нет ни в одном источнике")
        ask.append("Найти телефон отдела продаж")

    if s.get("emails"):
        points += 25
        plus.append("есть почта для запроса КП")
    else:
        minus.append("нет почты")
        ask.append("Спросить почту для коммерческого предложения")

    if s.get("website"):
        points += 15
        plus.append("есть сайт")
    else:
        minus.append("нет сайта")

    if s.get("hours"):
        points += 10
        plus.append("известны часы работы")
    else:
        minus.append("часы работы неизвестны")

    socials = s.get("socials") or []
    if socials:
        points += 10
        plus.append("есть соцсети: " + ", ".join(item["title"] for item in socials[:2]))

    if not phones and not s.get("emails"):
        ask.append("Найти контакты вручную по ссылкам ниже")

    return _box(points, plus, minus, ask)


def _volume(s: dict) -> dict:
    points, plus, minus, ask = 0, [], [], []
    kind_class = s.get("kind_class") or "unknown"
    if kind_class == "producer":
        points += 40
        plus.append("собственное производство")
    elif kind_class == "wholesale":
        points += 35
        plus.append("оптовая база или дистрибьютор")
    elif kind_class == "retail":
        minus.append("розничная точка, опт под вопросом")
        ask.append("Спросить, отгружают ли оптом и работают ли с юрлицами")
    else:
        points += 10
        minus.append("тип поставщика не определён")
        ask.append("Уточнить, производство это или перепродажа")

    moq = s.get("moq")
    if moq:
        points += 25
        plus.append(f"минимальный заказ: {moq}")
        if (s.get("moq_value") or 0) and s["moq_value"] <= LOW_MOQ_KG:
            points += 10
            plus.append("низкий порог входа")
    else:
        minus.append("минимальный заказ неизвестен")
        ask.append("Уточнить минимальный заказ")

    if s.get("price_list"):
        points += 20
        plus.append("на сайте есть прайс-лист")
    elif s.get("price"):
        points += 15
        plus.append(f"цены: {s['price']}")
    else:
        minus.append("цен нет в открытых источниках")
        ask.append("Запросить прайс")

    branches = s.get("branches", 1)
    if branches > 1:
        points += 10
        plus.append(f"{branches} {domain.plural(branches, 'точка', 'точки', 'точек')} в городе")

    return _box(points, plus, minus, ask)


def _docs(s: dict) -> dict:
    points, plus, minus, ask = 0, [], [], []
    certs = s.get("certs") or []
    if certs:
        points += min(45, 15 * len(certs))
        plus.append("документы: " + ", ".join(certs[:3]))
    else:
        minus.append("документы не найдены")
        ask.append("Запросить декларацию ТР ТС и результаты лабораторных проверок")

    if s.get("inn") or s.get("ogrn"):
        points += 25
        plus.append("известны реквизиты")
    else:
        minus.append("нет ИНН и ОГРН")
        ask.append("Уточнить ИНН для проверки юрлица")

    legal = s.get("legal_name")
    if legal:
        points += 30
        plus.append(f"юрлицо подтверждено: {legal[:60]}")
    else:
        minus.append("юрлицо не сверено с реестрами")

    return _box(points, plus, minus, ask)


def _logistics(s: dict) -> dict:
    points, plus, minus, ask = 0, [], [], []
    distance = s.get("distance_km")
    if distance is None:
        points += 10
        minus.append("расстояние неизвестно")
    elif distance <= NEAR_KM:
        points += 40
        plus.append(f"{distance:.0f} км от центра города")
    elif distance <= CITY_KM:
        points += 30
        plus.append(f"{distance:.0f} км от центра города")
    elif distance <= REGION_KM:
        points += 20
        plus.append(f"{distance:.0f} км, пригород")
    else:
        points += 10
        minus.append(f"{distance:.0f} км от центра — далеко")

    if s.get("delivery"):
        points += 30
        plus.append(s["delivery"][:70])
    else:
        minus.append("условия доставки неизвестны")
        ask.append("Уточнить доставку и сроки")

    if s.get("geo"):
        points += 20
        plus.append(f"поставки: {s['geo']}")
    else:
        minus.append("география поставок неизвестна")

    if s.get("own_delivery"):
        points += 10
        plus.append("своя логистика")

    return _box(points, plus, minus, ask)


def _trust(s: dict) -> dict:
    points, plus, minus, ask = 0, [], [], []
    if s.get("verified"):
        points += 40
        plus.append(s.get("verified_by") or "контакты подтверждены")
    else:
        minus.append("контакты не подтверждены вторым источником")
        ask.append("Сверить контакты при первом звонке")

    sources = len(s.get("sources") or [])
    if sources >= 3:
        points += 35
        plus.append(f"{sources} источника данных")
    elif sources == 2:
        points += 25
        plus.append("два источника данных")
    else:
        minus.append("данные только из одного источника")

    days = s.get("checked_days_ago")
    if days is not None and days <= FRESH_DAYS:
        points += 25
        plus.append("данные свежие")
    elif days is not None:
        minus.append(f"данные не обновлялись {int(days)} дней")

    if s.get("about"):
        points += 10
        plus.append("есть описание компании")

    return _box(points, plus, minus, ask)
