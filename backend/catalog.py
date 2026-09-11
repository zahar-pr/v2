from dataclasses import dataclass


@dataclass(frozen=True)
class Category:
    id: str
    title: str
    tags: tuple[tuple[str, str], ...]


CATEGORIES = (
    Category(
        "wholesale",
        "Оптовые базы продуктов",
        (
            ("shop", "wholesale"),
            ("wholesale", "food"),
            ("wholesale", "supermarket"),
            ("shop", "trade"),
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
        "bakery", "Хлеб и выпечка", (("craft", "bakery"), ("shop", "bakery"), ("shop", "pastry"))
    ),
    Category(
        "confectionery",
        "Кондитерские изделия",
        (("shop", "confectionery"), ("craft", "confectionery"), ("shop", "chocolate")),
    ),
    Category(
        "drinks",
        "Напитки и вода",
        (("shop", "beverages"), ("shop", "water"), ("craft", "brewery")),
    ),
    Category(
        "packaging",
        "Пищевая упаковка",
        (("shop", "packaging"), ("craft", "packaging"), ("shop", "houseware")),
    ),
)

PLACES = (
    "Москва",
    "Санкт-Петербург",
    "Екатеринбург",
    "Казань",
    "Новосибирск",
    "Нижний Новгород",
    "Краснодар",
    "Ростов-на-Дону",
    "Самара",
    "Челябинск",
    "Воронеж",
    "Пермь",
    "Тюмень",
    "Уфа",
    "Красноярск",
    "Сочи",
)

DEFAULT_CATEGORY = "drinks"
DEFAULT_PLACE = "Екатеринбург"

KIND_TITLES = {
    "wholesale": "Оптовая база",
    "trade": "Оптовая торговля",
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
    "packaging": "Упаковка",
    "houseware": "Посуда и упаковка",
}

UNKNOWN_KIND = "Организация"


def category(category_id: str) -> Category | None:
    return next((c for c in CATEGORIES if c.id == category_id), None)
