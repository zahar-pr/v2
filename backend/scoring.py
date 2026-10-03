import time
from dataclasses import dataclass

import domain
import safety

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
    Factor(
        "safety",
        "Санитарная история",
        "Не травила ли компания людей и чем это подтверждается",
    ),
    Factor("reputation", "Репутация компании", "Что о компании говорят реестры и отзывы"),
    Factor("reach", "Связь", "Как быстро вы дозвонитесь и кому писать"),
    Factor("volume", "Опт и объёмы", "Работает ли с оптом и известны ли условия"),
    Factor("docs", "Документы", "Пройдёт ли проверку службы качества"),
    Factor("logistics", "Логистика", "Довезёт ли до вашего города"),
    Factor("trust", "Достоверность данных", "Насколько полны и свежи сами данные"),
)

PRESETS = {
    "balanced": {
        "title": "Сбалансировано",
        "hint": "Сначала безопасность еды и репутация, потом опт, документы и доставка",
        "weights": {
            "safety": 26,
            "reputation": 22,
            "volume": 16,
            "docs": 13,
            "logistics": 11,
            "reach": 8,
            "trust": 4,
        },
    },
    "safe": {
        "title": "Безопасность еды",
        "hint": "Сначала те, у кого чистая санитарная история и документы на продукцию",
        "weights": {
            "safety": 46,
            "docs": 20,
            "reputation": 16,
            "trust": 8,
            "volume": 5,
            "logistics": 3,
            "reach": 2,
        },
    },
    "trusted": {
        "title": "Проверенные компании",
        "hint": "Сначала те, о ком есть отзывы и чистая история в реестрах",
        "weights": {
            "reputation": 34,
            "safety": 24,
            "docs": 16,
            "trust": 10,
            "volume": 8,
            "reach": 5,
            "logistics": 3,
        },
    },
    "urgent": {
        "title": "Позвонить сегодня",
        "hint": "Сначала те, у кого есть телефон, часы работы и кто рядом",
        "weights": {
            "reach": 38,
            "logistics": 16,
            "safety": 14,
            "volume": 14,
            "reputation": 10,
            "trust": 5,
            "docs": 3,
        },
    },
    "docs": {
        "title": "Нужны документы",
        "hint": "Сначала те, у кого есть декларации, реквизиты и подтверждённое юрлицо",
        "weights": {
            "docs": 36,
            "safety": 24,
            "reputation": 16,
            "volume": 10,
            "reach": 8,
            "trust": 4,
            "logistics": 2,
        },
    },
    "volume": {
        "title": "Нужен опт",
        "hint": "Сначала производства и базы с понятным минимальным заказом",
        "weights": {
            "volume": 38,
            "safety": 16,
            "logistics": 14,
            "reach": 12,
            "reputation": 12,
            "docs": 6,
            "trust": 2,
        },
    },
    "near": {
        "title": "Везут быстро",
        "hint": "Сначала те, кто рядом, возит сам и отгружает день в день",
        "weights": {
            "logistics": 38,
            "reach": 18,
            "safety": 14,
            "volume": 14,
            "reputation": 10,
            "docs": 4,
            "trust": 2,
        },
    },
}
DEFAULT_PRESET = "balanced"

TRUSTED = "trusted"
BLOCKED = "blocked"

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
        "safety": _safety(supplier),
        "reputation": _reputation(supplier),
        "reach": _reach(supplier),
        "volume": _volume(supplier),
        "docs": _docs(supplier),
        "logistics": _logistics(supplier),
        "trust": _trust(supplier),
    }


def total(scores: dict, weights: dict, supplier: dict | None = None) -> int:
    if (supplier or {}).get("trust_tier") == BLOCKED:
        return 0

    weight_sum = sum(weights.values()) or 1
    points = sum(scores[factor.id]["score"] * weights.get(factor.id, 0) for factor in FACTORS)
    score = round(points / weight_sum)

    # Санитарное решение — не один из факторов, а потолок: сколько бы ни было
    # телефонов и деклараций, поставщик с остановленным цехом наверх не всплывает.
    cap = scores.get("safety", {}).get("cap", 100)
    score = min(score, cap)

    if (supplier or {}).get("trust_tier") == TRUSTED and cap >= 100:
        return 100
    return score


def verdict_of(score: int, supplier: dict | None = None) -> tuple[str, str]:
    state = safety.state_of(supplier or {})
    if state["state"] == safety.BANNED:
        return "blocked", "Не брать: действует санитарное решение"
    if state["state"] == safety.INCIDENT:
        return "risky", "Был санитарный инцидент"

    tier = (supplier or {}).get("trust_tier") or ""
    if tier == TRUSTED:
        named = (supplier or {}).get("clients") or []
        return "trusted", "Проверенный поставщик сетей" if named else "Крупный поставщик HoReCa"
    if tier == BLOCKED:
        return "blocked", "Не рекомендуем: санкции надзора"
    return next((level, text) for limit, level, text in VERDICTS if score >= limit)


class Tally:
    def __init__(self):
        self.points = 0
        self.strengths: list[str] = []
        self.gaps: list[str] = []
        self.questions: list[str] = []

    def add(self, points: int, strength: str = "") -> "Tally":
        self.points += points
        if strength:
            self.strengths.append(strength)
        return self

    def lack(self, gap: str, question: str = "") -> "Tally":
        self.gaps.append(gap)
        if question:
            self.questions.append(question)
        return self

    def ask(self, question: str) -> "Tally":
        self.questions.append(question)
        return self

    def box(self) -> dict:
        return {
            "score": max(0, min(100, self.points)),
            "plus": self.strengths,
            "minus": self.gaps,
            "ask": self.questions,
        }


def _safety(s: dict) -> dict:
    """Единственный фактор, который может обнулить карточку целиком."""
    state = safety.state_of(s)
    tally = Tally()
    tally.add(state["score"])
    if state["state"] in (safety.BANNED, safety.INCIDENT):
        tally.lack(state["title"].lower(), "Запросить протоколы лаборатории за последний квартал")
    else:
        tally.add(0, state["title"].lower())
        docs = safety.food_docs(s)
        if docs:
            tally.add(0, "документы на продукцию: " + ", ".join(docs[:3]))
        else:
            tally.lack(
                "документов на продукцию в открытых источниках нет",
                "Запросить декларацию ТР ТС и протоколы испытаний",
            )
    box = tally.box()
    box["cap"] = state["cap"]
    box["state"] = state["state"]
    return box


def _reputation(s: dict) -> dict:
    tally = Tally()
    _rate_curated(tally, s)
    _rate_reviews(tally, s)
    _rate_team(tally, s)
    _rate_registry(tally, s)
    return tally.box()


def _rate_curated(tally: Tally, s: dict) -> None:
    """Кураторский список: поставщики сетей и те, кому приостанавливали работу."""
    tier = s.get("trust_tier") or ""
    clients = s.get("clients") or []
    if tier == TRUSTED:
        where = ", ".join(clients[:3])
        tally.add(
            60,
            f"поставщик сетей: {where}" if where else "крупный федеральный поставщик HoReCa",
        )


def _rate_reviews(tally: Tally, s: dict) -> None:
    rating = s.get("rating") if s.get("reviews_source") else None
    if not rating:
        tally.lack(
            "оценок в справочниках отзывов не нашлось", "Посмотреть отзывы по ссылкам в карточке"
        )
        return

    where = s.get("reviews_source") or "справочник"
    counted = f" по {s['reviews']} отзывам" if s.get("reviews") else ""
    if rating >= 4.5:
        tally.add(25, f"оценка {rating} из 5 на {where}{counted}")
    elif rating >= 4:
        tally.add(20, f"оценка {rating} из 5 на {where}{counted}")
    elif rating >= 3.5:
        tally.add(12, f"средняя оценка {rating} из 5 на {where}{counted}")
    else:
        tally.lack(
            f"низкая оценка {rating} из 5 на {where}{counted}",
            "Прочитать отзывы: оценка ниже тройки",
        )


def _rate_team(tally: Tally, s: dict) -> None:
    count = s.get("comments_count") or 0
    rating = s.get("comments_rating")
    if not count:
        tally.lack(
            "команда ещё не оставляла комментариев", "Записать вывод в комментарий после звонка"
        )
        return

    word = domain.plural(count, "комментарий", "комментария", "комментариев")
    if not rating:
        tally.add(8, f"{count} {word} от команды")
    elif rating >= 4:
        tally.add(25, f"коллеги оценили на {rating} из 5 ({count} {word})")
    elif rating >= 3:
        tally.add(15, f"коллеги оценили на {rating} из 5 ({count} {word})")
    else:
        tally.add(0, f"коллеги оценили на {rating} из 5 ({count} {word})")
        tally.lack(f"низкая оценка команды: {rating} из 5")


def _rate_registry(tally: Tally, s: dict) -> None:
    status = s.get("legal_status") or ""
    if s.get("legal_active"):
        tally.add(20, status.lower() if status else "действующее юрлицо по данным ФНС")
    elif status:
        tally.lack(f"статус в ФНС: {status.lower()}", "Проверить, действует ли юрлицо")
    else:
        tally.lack("юрлицо не найдено в реестрах ФНС")

    founded = s.get("founded")
    if not founded:
        tally.lack("дата регистрации неизвестна")
    else:
        age = max(0, domain.CURRENT_YEAR - int(founded))
        years = f"на рынке {age} {domain.plural(age, 'год', 'года', 'лет')}"
        if age >= 10:
            tally.add(20, years)
        elif age >= 5:
            tally.add(15, years)
        elif age >= 2:
            tally.add(8, years)
        else:
            tally.lack("компания зарегистрирована меньше двух лет назад")

    okved = s.get("okved") or ""
    if okved:
        name = (s.get("okved_name") or "").strip()
        tally.add(10, f"ОКВЭД {okved}: {name[:70]}" if name else f"ОКВЭД {okved}")


def _reach(s: dict) -> dict:
    tally = Tally()
    phones = s.get("phones") or []
    if phones:
        word = domain.plural(len(phones), "телефон", "телефона", "телефонов")
        text = f"телефон: {phones[0]}" if len(phones) == 1 else f"{len(phones)} {word}"
        tally.add(45 + (5 if len(phones) > 1 else 0), text)
    else:
        tally.lack("телефона нет ни в одном источнике", "Найти телефон отдела продаж")

    if s.get("emails"):
        tally.add(25, "есть почта для запроса КП")
    else:
        tally.lack("нет почты", "Спросить почту для коммерческого предложения")

    tally.add(15, "есть сайт") if s.get("website") else tally.lack("нет сайта")
    if s.get("hours"):
        tally.add(10, "известны часы работы")
    else:
        tally.lack("часы работы неизвестны")

    socials = s.get("socials") or []
    if socials:
        tally.add(10, "есть соцсети: " + ", ".join(item["title"] for item in socials[:2]))
    if not phones and not s.get("emails"):
        tally.ask("Найти контакты вручную по ссылкам ниже")
    return tally.box()


def _volume(s: dict) -> dict:
    tally = Tally()
    kind = s.get("kind_class") or "unknown"
    if kind == "producer":
        tally.add(40, "собственное производство")
    elif kind == "wholesale":
        tally.add(35, "оптовая база или дистрибьютор")
    elif kind == "retail":
        tally.lack(
            "розничная точка, опт под вопросом",
            "Спросить, отгружают ли оптом и работают ли с юрлицами",
        )
    else:
        tally.add(10).lack(
            "тип поставщика не определён", "Уточнить, производство это или перепродажа"
        )

    moq = s.get("moq")
    if moq:
        tally.add(25, f"минимальный заказ: {moq}")
        if (s.get("moq_value") or 0) and s["moq_value"] <= LOW_MOQ_KG:
            tally.add(10, "низкий порог входа")
    else:
        tally.lack("минимальный заказ неизвестен", "Уточнить минимальный заказ")

    if s.get("price_list"):
        tally.add(20, "на сайте есть прайс-лист")
    elif s.get("price"):
        tally.add(15, f"цены: {s['price']}")
    else:
        tally.lack("цен нет в открытых источниках", "Запросить прайс")

    branches = s.get("branches", 1)
    if branches > 1:
        word = domain.plural(branches, "точка", "точки", "точек")
        tally.add(10, f"{branches} {word} в городе")
    return tally.box()


def _docs(s: dict) -> dict:
    tally = Tally()
    certs = s.get("certs") or []
    if certs:
        tally.add(min(45, 15 * len(certs)), "документы: " + ", ".join(certs[:3]))
    else:
        tally.lack(
            "документы не найдены", "Запросить декларацию ТР ТС и результаты лабораторных проверок"
        )

    if s.get("inn") or s.get("ogrn"):
        tally.add(25, "известны реквизиты")
    else:
        tally.lack("нет ИНН и ОГРН", "Уточнить ИНН для проверки юрлица")

    legal = s.get("legal_name")
    if legal:
        tally.add(30, f"юрлицо подтверждено: {legal[:60]}")
    else:
        tally.lack("юрлицо не сверено с реестрами")
    return tally.box()


def _logistics(s: dict) -> dict:
    tally = Tally()
    distance = s.get("distance_km")
    if distance is None:
        tally.add(10).lack("расстояние неизвестно")
    elif distance <= NEAR_KM:
        tally.add(40, f"{distance:.0f} км от центра города")
    elif distance <= CITY_KM:
        tally.add(30, f"{distance:.0f} км от центра города")
    elif distance <= REGION_KM:
        tally.add(20, f"{distance:.0f} км, пригород")
    else:
        tally.add(10).lack(f"{distance:.0f} км от центра — далеко")

    if s.get("delivery"):
        tally.add(30, s["delivery"][:70])
    else:
        tally.lack("условия доставки неизвестны", "Уточнить доставку и сроки")

    if s.get("geo"):
        tally.add(20, f"поставки: {s['geo']}")
    else:
        tally.lack("география поставок неизвестна")

    if s.get("own_delivery"):
        tally.add(10, "своя логистика")
    return tally.box()


def _trust(s: dict) -> dict:
    tally = Tally()
    if s.get("verified"):
        tally.add(40, s.get("verified_by") or "контакты подтверждены")
    else:
        tally.lack(
            "контакты не подтверждены вторым источником", "Сверить контакты при первом звонке"
        )

    sources = len(s.get("sources") or [])
    if sources >= 3:
        tally.add(35, f"{sources} источника данных")
    elif sources == 2:
        tally.add(25, "два источника данных")
    else:
        tally.lack("данные только из одного источника")

    days = s.get("checked_days_ago")
    if days is not None and days <= FRESH_DAYS:
        tally.add(25, "данные свежие")
    elif days is not None:
        tally.lack(f"данные не обновлялись {int(days)} дней")

    if s.get("about"):
        tally.add(10, "есть описание компании")
    return tally.box()
