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
        ),
    ),
    Category(
        "grain",
        "Мука, крупы, зерно",
        (("craft", "grinding_mill"), ("man_made", "silo"), ("shop", "grain")),
    ),
    Category(
        "dairy",
        "Молочное сырьё и сыры",
        (("shop", "dairy"), ("craft", "dairy"), ("shop", "cheese")),
    ),
    Category(
        "meat",
        "Мясо и птица",
        (("shop", "butcher"), ("industrial", "slaughterhouse"), ("craft", "slaughterhouse")),
    ),
    Category("fish", "Рыба и морепродукты", (("shop", "seafood"), ("shop", "fish"))),
    Category(
        "vegetables",
        "Овощи, фрукты, зелень",
        (("shop", "greengrocer"), ("shop", "farm"), ("shop", "vegetables")),
    ),
    Category(
        "bakery",
        "Хлеб и выпечка",
        (("craft", "bakery"), ("shop", "bakery"), ("shop", "pastry")),
    ),
    Category(
        "confectionery",
        "Кондитерские изделия",
        (("shop", "confectionery"), ("craft", "confectionery"), ("shop", "chocolate")),
    ),
    Category(
        "drinks",
        "Напитки и вода",
        (
            ("shop", "beverages"),
            ("shop", "water"),
            ("craft", "brewery"),
            ("craft", "winery"),
            ("shop", "coffee"),
            ("shop", "tea"),
        ),
    ),
    Category(
        "packaging",
        "Пищевая упаковка",
        (("shop", "packaging"), ("craft", "packaging"), ("shop", "houseware")),
    ),
)

CITIES = (
    City("Москва", "Москва и область"),
    City("Подольск", "Москва и область"),
    City("Тула", "Москва и область"),
    City("Санкт-Петербург", "Санкт-Петербург и область"),
    City("Великий Новгород", "Санкт-Петербург и область"),
    City("Краснодар", "Юг России"),
    City("Ростов-на-Дону", "Юг России"),
    City("Сочи", "Юг России"),
    City("Волгоград", "Юг России"),
    City("Воронеж", "Юг России"),
    City("Казань", "Поволжье"),
    City("Нижний Новгород", "Поволжье"),
    City("Самара", "Поволжье"),
    City("Уфа", "Поволжье"),
    City("Саратов", "Поволжье"),
    City("Екатеринбург", "Урал"),
    City("Челябинск", "Урал"),
    City("Пермь", "Урал"),
    City("Тюмень", "Урал"),
    City("Новосибирск", "Сибирь"),
    City("Красноярск", "Сибирь"),
    City("Омск", "Сибирь"),
    City("Барнаул", "Сибирь"),
    City("Иркутск", "Сибирь"),
    City("Мурманск", "Север"),
    City("Архангельск", "Север"),
)

REGIONS = (
    "Москва и область",
    "Санкт-Петербург и область",
    "Юг России",
    "Поволжье",
    "Урал",
    "Сибирь",
    "Север",
)

SORTS = (
    "По готовности",
    "По рейтингу данных",
    "По минимальному заказу",
    "По названию",
)

DEFAULT_CATEGORY = ANY
DEFAULT_REGION = ANY
DEFAULT_CITY = ANY

KIND_TITLES = {
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


def region_of(name: str) -> str:
    found = city(name)
    return found.region if found else ""


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
