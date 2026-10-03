"""Кабинет Goulash Tech — один аккаунт на всю команду, без логина.

Сервис делает не маркетплейс «для всех», а рабочее место конкретной компании:
Goulash Tech ведёт закупки для девятнадцати сетей общепита, и у каждой сети свой
набор продуктов и свой город. Поэтому поиск начинается не с пустой строки, а с
проекта: «Жизнь Март, Екатеринбург, готовая еда и молочка» — и выдача сразу
отфильтрована под эту задачу.

Авторизации нет намеренно: кабинет один, команда работает в общем пространстве,
статусы и заметки видят все. Город у проекта можно поменять — сети растут, и
закупка под новый город начинается с того же проекта.
"""

from dataclasses import dataclass

import catalog
import safety
import store
import team

COMPANY = "Goulash Tech"
BASE_CITY = "Екатеринбург"


@dataclass(frozen=True)
class Project:
    id: str
    chain: str
    kitchen: str  # что за кухня — объясняет набор категорий
    city: str  # пустой, если сеть в нескольких городах и город выбирает закупщик
    cats: tuple[str, ...]
    need: str  # что именно ищем для этой сети


# Категории выведены из кухни сети: суши — рыба, рис, соусы; пицца — сыр, мука,
# мясо; бургерная — мясо, булочки, заморозка. Город проставлен там, где он
# однозначен; в остальных проектах его выбирает закупщик.
PROJECTS = (
    Project(
        "zhizn-mart", "Жизнь Март", "магазины у дома с готовой едой", BASE_CITY,
        ("frozen", "dairy", "bakery", "meat", "vegetables"),
        "замена поставщикам готовой еды после санитарных проверок 2024 года",
    ),
    Project(
        "sushkof", "Сушкоф и пицца", "суши и пицца", BASE_CITY,
        ("fish", "dairy", "grain", "spices", "packaging"),
        "рыба и сыр с документами, плюс упаковка под доставку",
    ),
    Project(
        "up-sushi", "UP Sushi", "суши", "",
        ("fish", "grain", "spices", "packaging"),
        "лосось и рис стабильного качества, соусы оптом",
    ),
    Project(
        "sushisell", "СушиСелл", "суши", "",
        ("fish", "grain", "spices", "packaging"),
        "второй поставщик рыбы на подстраховку основного",
    ),
    Project(
        "sushiman", "Sushiman", "суши", "",
        ("fish", "grain", "spices"),
        "морепродукты и рис под сетевой объём",
    ),
    Project(
        "sushi-shef", "Суши Шеф", "суши", "",
        ("fish", "grain", "spices", "packaging"),
        "рыба и упаковка в один контракт",
    ),
    Project(
        "zhishi-sushi", "Жиши суши", "суши", "",
        ("fish", "grain", "spices"),
        "рыба с доставкой день в день",
    ),
    Project(
        "sayori", "Sayori", "паназиатская кухня", "",
        ("fish", "spices", "vegetables", "frozen"),
        "азиатские ингредиенты и овощи круглый год",
    ),
    Project(
        "yaponskij-domik", "Японский домик", "суши", "",
        ("fish", "grain", "spices"),
        "рыба и нори с запасом по срокам",
    ),
    Project(
        "yoyu", "ЁЮ", "суши и роллы", "",
        ("fish", "grain", "packaging"),
        "рыба и упаковка для доставки",
    ),
    Project(
        "ninja-pizza", "Ninja Pizza", "пицца", "Красноярск",
        ("dairy", "grain", "meat", "vegetables", "packaging"),
        "сыр и мука под пиццерию, пепперони",
    ),
    Project(
        "tich-pizza", "ТиЧ Пицца", "пицца", "",
        ("dairy", "grain", "meat", "vegetables"),
        "моцарелла и мука с понятным минимальным заказом",
    ),
    Project(
        "pizza-san", "Пицца Сан", "пицца", "",
        ("dairy", "grain", "meat", "packaging"),
        "сыр, тесто, коробки",
    ),
    Project(
        "magic-burger", "Magic Burger", "бургеры", "",
        ("meat", "bakery", "vegetables", "frozen", "dairy"),
        "котлеты и булочки, картофель фри",
    ),
    Project(
        "sytyj-korol", "Сытый Король", "бургеры", "",
        ("meat", "bakery", "frozen", "drinks"),
        "мясо и заморозка по цене ниже текущей",
    ),
    Project(
        "rolik", "Rolik", "роллы и бургеры", "",
        ("fish", "meat", "bakery", "packaging"),
        "рыба и мясо у одного поставщика",
    ),
    Project(
        "foodgarden", "FoodGarden", "фудкорт", "",
        ("vegetables", "meat", "dairy", "frozen", "drinks"),
        "овощи и зелень круглогодично",
    ),
    Project(
        "nemestnye", "Неместные", "кафе авторской кухни", "",
        ("vegetables", "meat", "dairy", "spices"),
        "локальные фермерские продукты",
    ),
    Project(
        "vesla", "VЁSLA", "рыбная кухня", "",
        ("fish", "vegetables", "spices"),
        "свежая рыба с ветеринарными документами",
    ),
)

BY_ID = {item.id: item for item in PROJECTS}


def card(project: Project) -> dict:
    cats = ",".join(project.cats)
    city = project.city
    found = store.count_for(category=cats, city=city, kinds=("producer", "wholesale", "unknown"))
    safe = store.count_for(
        category=cats, city=city, only_safe=True, kinds=("producer", "wholesale", "unknown")
    )
    return {
        "id": project.id,
        "chain": project.chain,
        "kitchen": project.kitchen,
        "city": city,
        "cityTitle": city or catalog.ANY_CITY_TITLE,
        "cats": list(project.cats),
        "catTitles": [catalog.title(item) for item in project.cats],
        "need": project.need,
        "found": found,
        "safe": safe,
        "incidents": incidents_of(project.chain),
    }


def incidents_of(chain: str) -> list[dict]:
    """Поставщики именно этой сети, попавшие под санитарные решения.

    Для закупщика это самая важная строка в проекте: он подбирает замену ровно
    тем, кого закрыли, и должен видеть, кого именно.
    """
    return [
        {
            "name": _name_of(item.key),
            "title": item.title,
            "date": safety._human_date(item.date),
            "active": safety.active(item),
            "source": item.source,
        }
        for item in safety.INCIDENTS
        if item.chain == chain
    ]


def _name_of(name_key: str) -> str:
    row = store.connect().execute(
        "SELECT name FROM suppliers WHERE name_key=? LIMIT 1", (name_key,)
    ).fetchone()
    return row["name"] if row else name_key


def overview() -> dict:
    counts = team.status_counts()
    projects = [card(item) for item in PROJECTS]
    return {
        "company": COMPANY,
        "city": BASE_CITY,
        "chains": len(PROJECTS),
        "projects": projects,
        "pipeline": counts,
        "working": counts.get("calling", 0),
        "quoted": counts.get("quoted", 0),
        "fit": counts.get("fit", 0),
        "rejected": counts.get("rejected", 0),
        "activity": activity(),
    }


def activity(limit: int = 8) -> list[dict]:
    """Последние действия команды — чтобы кабинет не выглядел пустым складом."""
    connection = store.connect()
    rows = connection.execute(
        "SELECT p.supplier_id, p.status, p.author, p.updated_at, s.name, s.city "
        "FROM pipeline p JOIN suppliers s ON s.id = p.supplier_id "
        "ORDER BY p.updated_at DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [
        {
            "supplierId": row["supplier_id"],
            "name": row["name"],
            "city": row["city"],
            "status": row["status"],
            "author": row["author"] or "команда",
            "at": row["updated_at"],
        }
        for row in rows
    ]
