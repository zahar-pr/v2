import re
from dataclasses import dataclass

WHOLESALE_WORDS = re.compile(r"опт|завод|комбинат|фабрик|производ|склад|торговый дом|агро", re.I)
NON_FOOD_WORDS = re.compile(
    r"металл|подшипник|автозапчаст|строит|сантехник|мебел|текстил|инструмент|шин[ыа]|bearing|ювелир|аптек",
    re.I,
)
CRITERIA = (
    (30, lambda s: bool(s.phones), "есть телефон", "нет телефона"),
    (20, lambda s: bool(s.website), "есть сайт", "нет сайта"),
    (20, lambda s: s.wholesale, "опт или производство", "похоже на розницу"),
    (15, lambda s: bool(s.emails), "есть email", "нет email"),
    (10, lambda s: bool(s.address), "есть адрес", "нет адреса"),
    (5, lambda s: bool(s.hours), "указаны часы работы", "часы работы неизвестны"),
)
VERDICTS = (
    (65, "high", "Звонить первым"),
    (40, "mid", "Хороший кандидат"),
    (0, "low", "Мало данных"),
)


class PlaceNotFound(Exception):
    pass


class SourceUnavailable(Exception):
    pass


@dataclass
class Rating:
    score: int
    level: str
    verdict: str
    plus: list[str]
    minus: list[str]


@dataclass
class Supplier:
    name: str
    kind: str
    address: str
    phones: list[str]
    emails: list[str]
    website: str
    hours: str
    wholesale: bool
    source: str
    source_title: str
    branches: int = 1
    rating: Rating | None = None


def looks_wholesale(name: str) -> bool:
    return bool(WHOLESALE_WORDS.search(name))


def is_food_related(name: str) -> bool:
    return not NON_FOOD_WORDS.search(name)


def rate(supplier: Supplier) -> Rating:
    score, plus, minus = 0, [], []
    for points, check, good, bad in CRITERIA:
        if check(supplier):
            score += points
            plus.append(good)
        else:
            minus.append(bad)
    level, verdict = next((level, text) for limit, level, text in VERDICTS if score >= limit)
    return Rating(score=score, level=level, verdict=verdict, plus=plus, minus=minus)
