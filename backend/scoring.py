import time
from dataclasses import dataclass

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
    Factor("reach", "Связь", "Как быстро вы дозвонитесь и кому писать"),
    Factor("volume", "Опт и объёмы", "Работает ли с оптом и известны ли условия"),
    Factor("docs", "Документы и юрлицо", "Пройдёт ли проверку службы качества"),
    Factor("logistics", "Логистика", "Довезёт ли до вашего города"),
    Factor("trust", "Достоверность", "Насколько данным можно верить"),
)

PRESETS = {
    "balanced": {
        "title": "Сбалансированно",
        "hint": "Ровный вес всех факторов",
        "weights": {"reach": 25, "volume": 25, "docs": 20, "logistics": 15, "trust": 15},
    },
    "urgent": {
        "title": "Дозвониться сегодня",
        "hint": "Вперёд выходят те, у кого есть телефон и часы работы",
        "weights": {"reach": 45, "volume": 15, "docs": 5, "logistics": 20, "trust": 15},
    },
    "docs": {
        "title": "Нужны документы",
        "hint": "Вперёд выходят с декларациями и реквизитами",
        "weights": {"reach": 15, "volume": 15, "docs": 45, "logistics": 5, "trust": 20},
    },
    "volume": {
        "title": "Нужен опт",
        "hint": "Вперёд выходят производства и оптовые базы",
        "weights": {"reach": 15, "volume": 45, "docs": 20, "logistics": 15, "trust": 5},
    },
    "near": {
        "title": "Ближе к городу",
        "hint": "Вперёд выходят те, кто рядом и возит сам",
        "weights": {"reach": 25, "volume": 15, "docs": 10, "logistics": 45, "trust": 5},
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


def _plural(n: int, one: str, few: str, many: str) -> str:
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not 10 <= n % 100 < 20:
        return few
    return many


def _box(points: int, plus: list, minus: list, ask: list) -> dict:
    return {
        "score": max(0, min(100, points)),
        "plus": plus,
        "minus": minus,
        "ask": ask,
    }


def _reach(s: dict) -> dict:
    points, plus, minus, ask = 0, [], [], []
    phones = s.get("phones") or []
    if phones:
        points += 45
        plus.append(
            f"телефон: {phones[0]}"
            if len(phones) == 1
            else f"{len(phones)} {_plural(len(phones), 'телефон', 'телефона', 'телефонов')}"
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
        plus.append(f"{branches} {_plural(branches, 'точка', 'точки', 'точек')} в городе")

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

    if s.get("egrul_name"):
        points += 20
        plus.append(f"юрлицо в ЕГРЮЛ: {s['egrul_name'][:60]}")
        if not s.get("egrul_closed"):
            points += 10
        else:
            minus.append("в ЕГРЮЛ есть запись о прекращении — проверить статус")
            ask.append("Проверить действующий статус юрлица")
    else:
        minus.append("юрлицо не сверено с ЕГРЮЛ")

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
