import re
import time

CURRENT_YEAR = time.gmtime().tm_year

NON_FOOD_WORDS = re.compile(
    r"металл|подшипник|автозапчаст|строит|сантехник|мебел|текстил|инструмент|шин[ыа]|"
    r"bearing|ювелир|аптек|одежд|обув|космети|бытов[ао]я хими|электрон|телефон",
    re.I,
)
FOOD_WORDS = re.compile(
    r"продукт|пищев|провиз|бакале|молок|молочн|сыр|масло|мяс|колбас|рыб|море|хлеб|пекарн|"
    r"выпечк|кондитер|конфет|шоколад|торт|сладост|напитк|вод[аыу]|сок|пиво|чай|кофе|"
    r"овощ|фрукт|зелен|ягод|специ|припра|мука|круп|зерн|яйц|птиц|заморозк|полуфабрикат|"
    r"кулинар|общепит|horeca|хорека|food|агро|ферм|сельхоз|упаковк|тар[аы]|гофр|посуд|"
    r"фасовк|ингредиент|сырь[ёе]|деликатес|консерв|сухофрукт|орех|мед\b|дрожж|соус|"
    r"майонез|кетчуп|сахар|соль|снек|чипс",
    re.I,
)
RETAIL_WORDS = re.compile(
    r"\b(магазин\w*|киоск\w*|павильон\w*|лар[её]к|лавка|буфет|кафе|ресторан\w*|"
    r"столовая|пиццери\w*|кофейн\w+|чайная|закусочн\w+)\b",
    re.I,
)
WHOLESALE_HINT = re.compile(r"оптов\w*|\bопт\b|cash|мелкоопт", re.I)
PRODUCER_TAGS = {"craft", "industrial", "man_made"}
PRODUCER_WORDS = re.compile(
    r"завод|комбинат|фабрик|производ|мельниц|сыроварн|пивоварн|винодель|коптильн|"
    r"агрофирм|агрокомплекс|птицефабрик|молзавод|мясокомбинат|хлебозавод|цех\b",
    re.I,
)
WHOLESALE_TAGS = {
    ("shop", "wholesale"),
    ("shop", "trade"),
    ("wholesale", "food"),
    ("wholesale", "supermarket"),
    ("shop", "food"),
}
WHOLESALE_WORDS_STRICT = re.compile(
    r"опт|база\b|склад|торговый дом|дистрибьют|cash|metro|selgros|поставщик|снабжен",
    re.I,
)
TYPES = {
    "producer": "Производство",
    "wholesale": "Оптовая база",
    "retail": "Розничная точка",
    "unknown": "Не определён",
}


class PlaceNotFound(Exception):
    pass


class SourceUnavailable(Exception):
    pass


def is_food_related(name: str) -> bool:
    return not NON_FOOD_WORDS.search(name)


def looks_food(text: str) -> bool:
    return bool(FOOD_WORDS.search(text))


def plural(n: int, one: str, few: str, many: str) -> str:
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not 10 <= n % 100 < 20:
        return few
    return many


def years_text(year: int) -> str:
    age = max(0, CURRENT_YEAR - year)
    return f"{age} {plural(age, 'год', 'года', 'лет')} (с {year})"


def year_of(date: str) -> int | None:
    parts = (date or "").split(".")
    return int(parts[2]) if len(parts) == 3 and parts[2].isdigit() else None


def with_source(supplier: dict, source_id: str, title: str, url: str, **extra) -> list[dict]:
    known = [item for item in (supplier.get("sources") or []) if item.get("id") != source_id]
    known.append({"id": source_id, "title": title, "url": url, **extra})
    return known


def name_key(name: str) -> str:
    return re.sub(r"[^a-zа-я0-9]", "", name.lower())


def classify(kind_tag: str, name: str) -> str:
    key, _, value = kind_tag.partition("=")
    if RETAIL_WORDS.search(name) and not WHOLESALE_HINT.search(name):
        return "retail"
    if not kind_tag:
        return (
            "producer"
            if PRODUCER_WORDS.search(name)
            else ("wholesale" if WHOLESALE_WORDS_STRICT.search(name) else "unknown")
        )
    if PRODUCER_WORDS.search(name):
        return "producer"
    if key in PRODUCER_TAGS:
        return "producer"
    if WHOLESALE_WORDS_STRICT.search(name) or (key, value) in WHOLESALE_TAGS:
        return "wholesale"
    if key == "shop":
        return "retail"
    return "unknown"


def type_title(kind_class: str) -> str:
    return TYPES.get(kind_class, TYPES["unknown"])


def haystack(supplier: dict) -> str:
    parts = [
        supplier.get("name", ""),
        supplier.get("kind", ""),
        supplier.get("city", ""),
        supplier.get("region", ""),
        supplier.get("address", ""),
        supplier.get("website", ""),
        " ".join(supplier.get("cats_titles", [])),
    ]
    return " ".join(part for part in parts if part).lower()
