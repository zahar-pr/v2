from dataclasses import dataclass


@dataclass(frozen=True)
class Category:
    id: str
    title: str
    tags: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class City:
    name: str
    region: str
    code: str


ANY = "all"
ANY_CATEGORY_TITLE = "Все категории"
ANY_REGION_TITLE = "Все регионы"
ANY_CITY_TITLE = "Все города"

CATEGORIES = (
    Category(
        "wholesale",
        "Оптовые базы продуктов",
        (
            ("shop", "wholesale"),
            ("wholesale", "food"),
            ("wholesale", "supermarket"),
            ("shop", "trade"),
            ("shop", "food"),
            ("amenity", "marketplace"),
        ),
    ),
    Category(
        "grain",
        "Мука, крупы, зерно",
        (
            ("craft", "grinding_mill"),
            ("craft", "oil_mill"),
            ("man_made", "silo"),
            ("shop", "grain"),
            ("industrial", "flour_mill"),
        ),
    ),
    Category(
        "dairy",
        "Молочное сырьё и сыры",
        (
            ("shop", "dairy"),
            ("craft", "dairy"),
            ("craft", "cheesemaker"),
            ("shop", "cheese"),
            ("industrial", "dairy"),
        ),
    ),
    Category(
        "meat",
        "Мясо и птица",
        (
            ("shop", "butcher"),
            ("craft", "butcher"),
            ("industrial", "slaughterhouse"),
            ("craft", "slaughterhouse"),
            ("industrial", "meat"),
        ),
    ),
    Category(
        "fish",
        "Рыба и морепродукты",
        (("shop", "seafood"), ("shop", "fish"), ("industrial", "fish")),
    ),
    Category(
        "vegetables",
        "Овощи, фрукты, зелень",
        (
            ("shop", "greengrocer"),
            ("shop", "farm"),
            ("shop", "vegetables"),
            ("craft", "agricultural"),
        ),
    ),
    Category(
        "bakery",
        "Хлеб и выпечка",
        (
            ("craft", "bakery"),
            ("shop", "bakery"),
            ("shop", "pastry"),
            ("craft", "pastry"),
            ("industrial", "bakery"),
        ),
    ),
    Category(
        "confectionery",
        "Кондитерские изделия",
        (
            ("shop", "confectionery"),
            ("craft", "confectionery"),
            ("craft", "chocolatier"),
            ("shop", "chocolate"),
        ),
    ),
    Category(
        "drinks",
        "Напитки и вода",
        (
            ("shop", "beverages"),
            ("shop", "water"),
            ("craft", "brewery"),
            ("craft", "winery"),
            ("craft", "distillery"),
            ("industrial", "brewery"),
            ("shop", "coffee"),
            ("shop", "tea"),
        ),
    ),
    Category(
        "frozen",
        "Заморозка и полуфабрикаты",
        (("shop", "frozen_food"), ("industrial", "cold_storage"), ("shop", "deli")),
    ),
    Category(
        "spices",
        "Специи и ингредиенты",
        (("shop", "spices"), ("shop", "herbs"), ("shop", "nuts"), ("shop", "honey")),
    ),
    Category(
        "packaging",
        "Пищевая упаковка",
        (
            ("shop", "packaging"),
            ("craft", "packaging"),
            ("shop", "houseware"),
            ("industrial", "packaging"),
        ),
    ),
)

CITIES = (
    City("Москва", "Москва и область", "77"),
    City("Подольск", "Москва и область", "50"),
    City("Тула", "Москва и область", "71"),
    City("Санкт-Петербург", "Санкт-Петербург и область", "78"),
    City("Великий Новгород", "Санкт-Петербург и область", "53"),
    City("Краснодар", "Юг России", "23"),
    City("Ростов-на-Дону", "Юг России", "61"),
    City("Сочи", "Юг России", "23"),
    City("Волгоград", "Юг России", "34"),
    City("Воронеж", "Юг России", "36"),
    City("Казань", "Поволжье", "16"),
    City("Нижний Новгород", "Поволжье", "52"),
    City("Самара", "Поволжье", "63"),
    City("Уфа", "Поволжье", "02"),
    City("Саратов", "Поволжье", "64"),
    City("Екатеринбург", "Урал", "66"),
    City("Челябинск", "Урал", "74"),
    City("Пермь", "Урал", "59"),
    City("Тюмень", "Урал", "72"),
    City("Новосибирск", "Сибирь", "54"),
    City("Красноярск", "Сибирь", "24"),
    City("Омск", "Сибирь", "55"),
    City("Барнаул", "Сибирь", "22"),
    City("Иркутск", "Сибирь", "38"),
    City("Мурманск", "Север", "51"),
    City("Архангельск", "Север", "29"),
)

OTHER_REGION = "Другие регионы"

REGIONS = (
    "Москва и область",
    "Санкт-Петербург и область",
    "Юг России",
    "Поволжье",
    "Урал",
    "Сибирь",
    "Север",
    OTHER_REGION,
)

AREA_REGIONS = {
    "МОСКВА": "Москва и область",
    "МОСКОВСКАЯ": "Москва и область",
    "ТУЛЬСКАЯ": "Москва и область",
    "КАЛУЖСКАЯ": "Москва и область",
    "ВЛАДИМИРСКАЯ": "Москва и область",
    "ТВЕРСКАЯ": "Москва и область",
    "РЯЗАНСКАЯ": "Москва и область",
    "ЯРОСЛАВСКАЯ": "Москва и область",
    "САНКТ-ПЕТЕРБУРГ": "Санкт-Петербург и область",
    "ЛЕНИНГРАДСКАЯ": "Санкт-Петербург и область",
    "НОВГОРОДСКАЯ": "Санкт-Петербург и область",
    "ПСКОВСКАЯ": "Санкт-Петербург и область",
    "КРАСНОДАРСКИЙ": "Юг России",
    "РОСТОВСКАЯ": "Юг России",
    "ВОЛГОГРАДСКАЯ": "Юг России",
    "ВОРОНЕЖСКАЯ": "Юг России",
    "СТАВРОПОЛЬСКИЙ": "Юг России",
    "КРЫМ": "Юг России",
    "АДЫГЕЯ": "Юг России",
    "БЕЛГОРОДСКАЯ": "Юг России",
    "ТАТАРСТАН": "Поволжье",
    "НИЖЕГОРОДСКАЯ": "Поволжье",
    "САМАРСКАЯ": "Поволжье",
    "БАШКОРТОСТАН": "Поволжье",
    "САРАТОВСКАЯ": "Поволжье",
    "УЛЬЯНОВСКАЯ": "Поволжье",
    "ПЕНЗЕНСКАЯ": "Поволжье",
    "ЧУВАШСКАЯ": "Поволжье",
    "МАРИЙ": "Поволжье",
    "МОРДОВИЯ": "Поволжье",
    "УДМУРТСКАЯ": "Поволжье",
    "КИРОВСКАЯ": "Поволжье",
    "ОРЕНБУРГСКАЯ": "Поволжье",
    "СВЕРДЛОВСКАЯ": "Урал",
    "ЧЕЛЯБИНСКАЯ": "Урал",
    "ПЕРМСКИЙ": "Урал",
    "ТЮМЕНСКАЯ": "Урал",
    "КУРГАНСКАЯ": "Урал",
    "НОВОСИБИРСКАЯ": "Сибирь",
    "КРАСНОЯРСКИЙ": "Сибирь",
    "ОМСКАЯ": "Сибирь",
    "АЛТАЙСКИЙ": "Сибирь",
    "ИРКУТСКАЯ": "Сибирь",
    "КЕМЕРОВСКАЯ": "Сибирь",
    "ТОМСКАЯ": "Сибирь",
    "МУРМАНСКАЯ": "Север",
    "АРХАНГЕЛЬСКАЯ": "Север",
    "КАРЕЛИЯ": "Север",
    "КОМИ": "Север",
    "ВОЛОГОДСКАЯ": "Север",
}

SORTS = (
    "По приоритету",
    "По расстоянию",
    "По минимальному заказу",
    "По названию",
)

DEFAULT_CATEGORY = ANY
DEFAULT_REGION = ANY
DEFAULT_CITY = ANY

KIND_TITLES = {
    "marketplace": "Рынок",
    "oil_mill": "Маслозавод",
    "flour_mill": "Мукомольный завод",
    "cheesemaker": "Сыроварня",
    "meat": "Мясопереработка",
    "distillery": "Завод напитков",
    "chocolatier": "Шоколадное производство",
    "agricultural": "Сельхозпроизводство",
    "frozen_food": "Заморозка",
    "cold_storage": "Холодильный склад",
    "deli": "Деликатесы и гастрономия",
    "spices": "Специи",
    "herbs": "Травы и приправы",
    "nuts": "Орехи и сухофрукты",
    "honey": "Мёд",
    "wholesale": "Оптовая база",
    "trade": "Оптовая торговля",
    "food": "Продукты",
    "grinding_mill": "Мельница",
    "silo": "Элеватор",
    "grain": "Зерно и крупы",
    "dairy": "Молочная продукция",
    "cheese": "Сыры",
    "butcher": "Мясо",
    "slaughterhouse": "Мясокомбинат",
    "seafood": "Рыба и морепродукты",
    "fish": "Рыба",
    "greengrocer": "Овощи и фрукты",
    "farm": "Фермерская продукция",
    "vegetables": "Овощи",
    "bakery": "Хлеб и выпечка",
    "pastry": "Выпечка и кондитерская",
    "confectionery": "Кондитерские изделия",
    "chocolate": "Шоколад",
    "beverages": "Напитки",
    "water": "Вода",
    "brewery": "Производство напитков",
    "winery": "Винодельня",
    "coffee": "Кофе",
    "tea": "Чай",
    "packaging": "Упаковка",
    "houseware": "Посуда и упаковка",
}

UNKNOWN_KIND = "Организация"

TAG_CATEGORIES: dict[tuple[str, str], tuple[str, ...]] = {}
for _category in CATEGORIES:
    for _tag in _category.tags:
        TAG_CATEGORIES[_tag] = TAG_CATEGORIES.get(_tag, ()) + (_category.id,)

ALL_TAGS = tuple(TAG_CATEGORIES)


def category(category_id: str) -> Category | None:
    return next((item for item in CATEGORIES if item.id == category_id), None)


def title(category_id: str) -> str:
    found = category(category_id)
    return found.title if found else category_id


def city(name: str) -> City | None:
    return next((item for item in CITIES if item.name == name), None)


def region_by_area(area: str) -> str:
    upper = (area or "").upper()
    for key, region in AREA_REGIONS.items():
        if key in upper:
            return region
    return OTHER_REGION


def pretty_area(area: str) -> str:
    clean = (area or "").replace("ГОРОД ФЕДЕРАЛЬНОГО ЗНАЧЕНИЯ ", "").strip()
    if not clean.isupper():
        return clean
    return " ".join(word[:1] + word[1:].lower() for word in clean.split())


def cities_of(region: str) -> tuple[str, ...]:
    if not region or region == ANY:
        return tuple(item.name for item in CITIES)
    return tuple(item.name for item in CITIES if item.region == region)


def categories_for(tags: dict) -> tuple[str, ...]:
    found: list[str] = []
    for key, value in tags.items():
        for category_id in TAG_CATEGORIES.get((key, value), ()):
            if category_id not in found:
                found.append(category_id)
    return tuple(found)
