import re

WHOLESALE_WORDS = re.compile(
    r"опт|завод|комбинат|фабрик|производ|склад|торговый дом|агро|дистрибьют|поставщик|база",
    re.I,
)
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
CRITERIA = (
    (25, lambda s: bool(s.get("phones")), "есть телефон", "нет телефона"),
    (15, lambda s: bool(s.get("website")), "есть сайт", "нет сайта"),
    (15, lambda s: bool(s.get("emails")), "есть email", "нет email"),
    (15, lambda s: bool(s.get("wholesale")), "опт или производство", "похоже на розницу"),
    (10, lambda s: bool(s.get("certs")), "есть документы", "документы не найдены"),
    (7, lambda s: bool(s.get("inn") or s.get("ogrn")), "есть реквизиты", "нет реквизитов"),
    (8, lambda s: bool(s.get("address")), "есть адрес", "нет адреса"),
    (5, lambda s: bool(s.get("hours")), "указаны часы работы", "часы работы неизвестны"),
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


def looks_wholesale(name: str) -> bool:
    return bool(WHOLESALE_WORDS.search(name))


def is_food_related(name: str) -> bool:
    return not NON_FOOD_WORDS.search(name)


def looks_food(text: str) -> bool:
    return bool(FOOD_WORDS.search(text))


def name_key(name: str) -> str:
    return re.sub(r"[^a-zа-я0-9]", "", name.lower())


def rate(supplier: dict) -> dict:
    score, plus, minus = 0, [], []
    for points, check, good, bad in CRITERIA:
        if check(supplier):
            score += points
            plus.append(good)
        else:
            minus.append(bad)
    level, verdict = next((level, text) for limit, level, text in VERDICTS if score >= limit)
    return {
        "score": score,
        "level": level,
        "verdict": verdict,
        "plus": plus,
        "minus": minus,
        "rating": round(score / 20, 1),
    }


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
