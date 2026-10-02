import ast
import os
import pathlib
import re
import subprocess
import sys
import time

os.environ["DB_PATH"] = "/tmp/provizia-test.db"
os.environ["PROVIZIA_WORKERS"] = "0"
os.environ["ADMIN_TOKEN"] = "secret"
if os.path.exists("/tmp/provizia-test.db"):
    os.remove("/tmp/provizia-test.db")

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

import db
import domain
import index
import main
import scoring
import store
from fastapi.testclient import TestClient
from sources import egrul, fns, wikidata, zoon

ok = []


def check(label, condition, extra=""):
    ok.append(bool(condition))
    print(("PASS " if condition else "FAIL ") + label + ("" if condition else f"  <- {extra}"))


def row(**kw):
    base = dict(
        id="",
        name="",
        name_key="",
        city="Казань",
        region="Поволжье",
        area="",
        cats=",bakery,",
        kind="Хлеб и выпечка",
        kind_tag="craft=bakery",
        kind_class="producer",
        address="Казань",
        phones=[],
        emails=[],
        socials=[],
        website="",
        hours="",
        wholesale=True,
        branches=1,
        lat=None,
        lon=None,
        source="https://osm.org/x",
        source_title="OpenStreetMap",
        sources=[{"id": "osm", "title": "OSM", "url": "u"}],
        distance_km=None,
        checked_at=time.time(),
    )
    base.update(kw)
    base["name_key"] = domain.name_key(base["name"])
    base["haystack"] = domain.haystack(base)
    return base


rows = [
    row(
        id="a",
        name="Хлебозавод Полный",
        phones=["+7 843 111-11-11", "+7 843 111-11-12"],
        emails=["opt@zavod.ru"],
        website="https://zavod.ru",
        hours="08:00-18:00",
        distance_km=5.0,
    ),
    row(
        id="b",
        name="Булочная Розница",
        phones=["+7 843 222-22-22"],
        kind_class="retail",
        kind_tag="shop=bakery",
        wholesale=False,
        distance_km=3.0,
    ),
    row(
        id="c",
        name="Оптбаза Дальняя",
        phones=["+7 843 333-33-33"],
        emails=["sale@baza.ru"],
        website="https://baza.ru",
        kind_class="wholesale",
        kind_tag="shop=wholesale",
        cats=",wholesale,",
        distance_km=55.0,
    ),
    row(id="d", name="Тихий Цех", distance_km=8.0),
    row(id="t", name="Сетевой Поставщик", phones=["+7 843 444-44-44"], distance_km=7.0),
    row(id="x", name="Закрытый Цех", phones=["+7 843 555-55-55"], distance_km=9.0),
]
store.save_indexed(rows)
store.save_enrichment(
    "a",
    {
        "certs": ["Декларация ТР ТС", "ХАССП"],
        "moq": "от 200 кг",
        "moq_value": 200.0,
        "price": "от 190 ₽/кг",
        "price_list": "https://zavod.ru/price.xlsx",
        "delivery": "Своя логистика, ежедневно",
        "own_delivery": 1,
        "geo": "ПФО",
        "inn": "1655123456",
        "legal_name": 'ООО "ХЛЕБОЗАВОД"',
        "manager": "Иванов И.И. (директор)",
        "legal_status": "Действующая организация",
        "legal_active": 1,
        "okved": "10.71",
        "okved_name": "Производство хлеба",
        "years": "22 года (с 2004)",
        "founded": 2004,
        "about": "Хлебобулочная продукция",
    },
)
store.set_verified("a", True, "контакты подтверждены на сайте поставщика")
store.save_enrichment("c", {"delivery": "ТК по России", "geo": "Вся Россия"})
for item in store.unscored(50):
    index.score_one(item)

client = TestClient(main.app)

flakes = subprocess.run(
    [sys.executable, "-m", "pyflakes", str(ROOT / "backend")],
    capture_output=True,
    text=True,
)
if flakes.returncode in (0, 1):
    report = flakes.stdout.strip()
    check("бэкенд без неиспользуемого и неопределённого", not report, report.splitlines()[:4])
else:
    print("SKIP pyflakes не установлен")

missing = []
for source in sorted((ROOT / "backend").rglob("*.py")):
    for node in ast.walk(ast.parse(source.read_text())):
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            module = sys.modules.get(node.value.id)
            known = (
                "db",
                "catalog",
                "scoring",
                "domain",
                "payload",
                "index",
                "egrul",
                "fns",
                "zoon",
                "wikidata",
            )
            if node.value.id in known:
                target = module or sys.modules.get(f"sources.{node.value.id}")
                if target and not hasattr(target, node.attr):
                    missing.append(f"{source.name}: {node.value.id}.{node.attr}")
check("модули не зовут несуществующие функции", not missing, missing[:4])

meta = client.get("/api/meta").json()
check("мета: 6 факторов", len(meta["factors"]) == 6, [f["id"] for f in meta["factors"]])
check("мета: фактор репутации", any(f["id"] == "reputation" for f in meta["factors"]))
check("мета: 6 пресетов", len(meta["presets"]) == 6)
check("веса пресетов дают 100", all(sum(p["weights"].values()) == 100 for p in meta["presets"]))
check(
    "веса не поровну",
    len({*meta["presets"][0]["weights"].values()}) > 3,
    meta["presets"][0]["weights"],
)
check(
    "мета: типы",
    {k["id"] for k in meta["kinds"]} == {"producer", "wholesale", "retail", "unknown"},
)
check(
    "мета: статусы",
    {s["id"] for s in meta["statuses"]} == {"new", "calling", "quoted", "fit", "rejected"},
)
check("мета: по умолчанию без розницы", "retail" not in meta["defaults"]["kinds"])
check("мета: города по регионам", isinstance(meta["cities"], dict) and len(meta["regions"]) >= 9)

base = client.get("/api/suppliers", params={"kinds": "producer,wholesale,unknown"}).json()
check("фильтр типа прячет розницу", all(i["type"] != "retail" for i in base["items"]))
check(
    "полный поставщик первый",
    base["items"][0]["id"] == "a",
    [(i["id"], i["score"]) for i in base["items"]],
)
card = base["items"][0]
check("раскладка из 6 факторов", len(card["factors"]) == 6)
check("у фактора есть вес", card["factors"][0]["weight"] > 0)
check("есть «что уточнить»", isinstance(card["ask"], list))
check("тип подписан", card["typeTitle"] == "Производство")
check("расстояние", card["distanceKm"] == 5.0)
check("юрлицо", card["legalName"].startswith("ООО"))
check("руководитель", "Иванов" in card["legalHead"])
check("ОКВЭД", card["okved"] == "10.71")
check("статус ФНС", card["legalActive"])
check("прайс-лист", card["priceList"].endswith(".xlsx"))
check("ссылки на отзывы", len(card["reviewLinks"]) == 3)
check("ранг", card["rank"] == 1)

for preset in ("urgent", "docs", "volume", "near", "trusted"):
    answer = client.get("/api/suppliers", params={"preset": preset}).json()
    check(
        f"пресет {preset} отдаёт свои веса",
        sum(answer["weights"].values()) == 100,
        answer["weights"],
    )
check(
    "пресеты меняют балл",
    client.get("/api/suppliers", params={"preset": "near"}).json()["items"][0]["score"]
    != client.get("/api/suppliers", params={"preset": "docs"}).json()["items"][0]["score"],
)

check(
    "фильтр документов",
    client.get("/api/suppliers", params={"onlyDocs": "true"}).json()["total"] == 1,
)
check(
    "фильтр контактов",
    client.get("/api/suppliers", params={"onlyContacts": "true"}).json()["total"] == 5,
)
check(
    "поиск по строке", client.get("/api/suppliers", params={"q": "оптбаза"}).json()["total"] == 1
)
check(
    "сортировка по расстоянию",
    client.get("/api/suppliers", params={"sort": "По расстоянию"}).json()["items"][0]["id"] == "b",
)
paged = client.get("/api/suppliers", params={"perPage": 2, "page": 2}).json()
check("пагинация", paged["page"] == 2 and paged["pages"] == 3)
facets = client.get("/api/suppliers").json()["facets"]
check("фасеты: типы", facets["types"]["producer"] == 4)
check("фасеты: категории", facets["cats"]["bakery"] == 5 and facets["cats"]["wholesale"] == 1)
check(
    "фасеты категорий не зависят от выбранной категории",
    client.get("/api/suppliers", params={"category": "wholesale"}).json()["facets"]["cats"][
        "bakery"
    ]
    == 5,
)
check(
    "несколько категорий разом",
    client.get("/api/suppliers", params={"category": "bakery,wholesale"}).json()["total"] == 6,
)

# кураторские метки ставим здесь, чтобы не сдвигать порядок в тестах выше
store.save_enrichment(
    "t",
    {
        "trust_tier": "trusted",
        "trust_note": "Поставляет для: Burger King.",
        "clients": ["Burger King"],
        "products": ["котлеты"],
    },
)
store.save_enrichment(
    "x",
    {
        "trust_tier": "blocked",
        "trust_note": "Приостановка 60 суток.",
        "incident": {"risk": "Высокий", "sanction": "Приостановка 60 суток"},
    },
)
for item in ("t", "x"):
    index.score_one(store.get(item))

cards = {item["id"]: item for item in client.get("/api/suppliers").json()["items"]}
check("проверенный поставщик: балл 100", cards["t"]["score"] == 100, cards["t"]["score"])
check("проверенный поставщик: вердикт", cards["t"]["level"] == "trusted", cards["t"]["level"])
check("проверенный поставщик: клиенты", cards["t"]["clients"] == ["Burger King"])
check("санкции надзора: балл 0", cards["x"]["score"] == 0, cards["x"]["score"])
check("санкции надзора: вердикт", cards["x"]["level"] == "blocked", cards["x"]["level"])
check(
    "санкции надзора: причина видна",
    "Приостановка" in cards["x"]["incident"].get("sanction", ""),
    cards["x"]["incident"],
)
check(
    "репутация весит больше всех в «Сбалансировано»",
    max(
        scoring.PRESETS["balanced"]["weights"],
        key=scoring.PRESETS["balanced"]["weights"].get,
    )
    == "reputation",
    scoring.PRESETS["balanced"]["weights"],
)
check(
    "пресет переименован",
    scoring.PRESETS["balanced"]["title"] == "Сбалансировано",
    scoring.PRESETS["balanced"]["title"],
)

order = client.get("/api/suppliers").json()["items"]
check(
    "проверенные идут первыми",
    [item["id"] for item in order][:1] == ["t"],
    [(i["id"], i["level"]) for i in order],
)
by_name = client.get(
    "/api/suppliers?sort=%D0%9F%D0%BE%20%D0%BD%D0%B0%D0%B7%D0%B2%D0%B0%D0%BD%D0%B8%D1%8E"
).json()["items"]
check(
    "проверенные первыми и при сортировке по названию",
    by_name[0]["id"] == "t" and by_name[-1]["id"] == "x",
    [(i["id"], i["name"]) for i in by_name],
)
check(
    "вердикт без названных сетей честнее",
    scoring.verdict_of(100, {"trust_tier": "trusted", "clients": []})[1]
    == "Крупный поставщик HoReCa",
)

app_jsx = (ROOT / "frontend" / "src" / "App.jsx").read_text()
main_py = (ROOT / "backend" / "main.py").read_text()
intro_jsx = (ROOT / "frontend" / "src" / "components" / "Intro.jsx").read_text()
logos_jsx = (ROOT / "frontend" / "src" / "components" / "ClientLogos.jsx").read_text()
help_jsx = (ROOT / "frontend" / "src" / "components" / "HelpButton.jsx").read_text()
check(
    "памятка встречает на каждом заходе",
    "provizia_intro" not in app_jsx and "if (meta) setIntroOpen(true)" in app_jsx,
)
check("памятка берёт веса из меты, а не из текста", "weights[id]" in intro_jsx)
check(
    "памятка объясняет зелёные и красные",
    "Зелёные" in intro_jsx and "Красные" in intro_jsx and "Роспотребнадзор" in intro_jsx,
)

index_html = (ROOT / "frontend" / "index.html").read_text()
check("есть robots.txt", (ROOT / "frontend" / "public" / "robots.txt").exists())
check("есть карта сайта", (ROOT / "frontend" / "public" / "sitemap.xml").exists())
check(
    "роботам не закрыт /api: без него страница не отрисуется",
    "Disallow: /api" not in (ROOT / "frontend" / "public" / "robots.txt").read_text(),
)
check("JSON закрыт от индексации заголовком", "X-Robots-Tag" in main_py)
check(
    "страница без JS не пустая",
    'class="seo"' in index_html and len(re.sub(r"<[^>]+>", "", index_html)) > 800,
)
check(
    "разметка для поиска на месте",
    'rel="canonical"' in index_html
    and 'property="og:title"' in index_html
    and "application/ld+json" in index_html,
)

css = (ROOT / "frontend" / "src" / "styles" / "global.css").read_text()
check("памятку можно открыть кнопкой «?»", "HelpButton" in app_jsx and "helper" in help_jsx)
check("памятка улетает в кнопку", "--fly-x" in intro_jsx and "helper--caught" in intro_jsx)
check("лента логотипов печатается дважды", logos_jsx.count("line(") == 2)
check(
    "у логотипов нет белой плашки",
    "background: #ffffff" not in css[css.index(".clients {") : css.index(".search {")],
)
check("тёмная тема объявлена", ":root[data-theme='dark']" in css)
check("светлая и тёмная схемы для системных элементов", css.count("color-scheme") == 2)
palette = css[css.index(":root {") : css.index("* { box-sizing")]
outside = re.findall(r"#[0-9a-fA-F]{3,8}", css.replace(palette, ""))
dark_block = css[css.index(":root[data-theme='dark']") :]
outside = [value for value in outside if value not in dark_block]
check("цвета только в палитре, не в правилах", not outside, outside[:6])

showcase = client.get("/api/meta").json()["showcase"]
check("витрина сравнения: пара", len(showcase) == 2, showcase)
check(
    "витрина сравнения: общий продукт",
    bool(set(showcase[0]["cats"]) & set(showcase[1]["cats"])),
    [item["cats"] for item in showcase],
)
check(
    "витрина сравнения: разные компании",
    showcase[0]["id"] != showcase[1]["id"] and showcase[0]["site"] != showcase[1]["site"],
)

empty = client.get("/api/suppliers", params={"onlyDocs": "true", "q": "несуществующее"}).json()
check(
    "пустая выдача подсказывает, что снять",
    empty["total"] == 0 and len(empty.get("relax", [])) > 0,
    empty.get("relax"),
)

client.post("/api/profile", json={"name": "Захар"})
check("профиль сохранён", client.get("/api/profile").json()["name"] == "Захар")
saved = client.post("/api/pipeline", json={"supplierId": "c", "status": "rejected"}).json()
check("статус сохранён", saved["status"] == "rejected" and saved["counts"]["rejected"] == 1)
other = TestClient(main.app)
seen = other.get("/api/suppliers").json()["items"]
check("статус виден команде", any(i["id"] == "c" and i["status"] == "rejected" for i in seen))
check("автор статуса", next(i for i in seen if i["id"] == "c")["statusAuthor"] == "Захар")
check("возраст статуса", next(i for i in seen if i["id"] == "c")["statusDays"] == 0)
check(
    "фильтр по статусу",
    client.get("/api/suppliers", params={"status": "rejected"}).json()["total"] == 1,
)

client.post("/api/notes", json={"supplierId": "a", "text": "Ждём КП до 25.09"})
team = next(i for i in other.get("/api/suppliers").json()["items"] if i["id"] == "a")
check("заметка видна команде", team["note"] == "Ждём КП до 25.09")
check("автор заметки", team["noteAuthor"] == "Захар")

client.post("/api/checks", json={"supplierId": "a", "question": "Запросить прайс", "done": True})
check(
    "чек-лист командный",
    "Запросить прайс"
    in next(i for i in other.get("/api/suppliers").json()["items"] if i["id"] == "a")[
        "checksDone"
    ],
)

posted = client.post(
    "/api/comments", json={"supplierId": "a", "text": "Звонили, МОЗ 500 кг", "rating": 4}
).json()
check("комментарий создан", posted["rating"] == 4 and posted["mine"])
other.post(
    "/api/comments",
    json={"supplierId": "a", "text": "Отгрузили в срок", "rating": 5, "author": "Ирина"},
)
check("комментарии видны всем", len(client.get("/api/comments/a").json()["items"]) == 2)
check(
    "пустой комментарий -> 400",
    client.post("/api/comments", json={"supplierId": "a", "text": " "}).status_code == 400,
)
check(
    "оценка вне шкалы -> 400",
    client.post("/api/comments", json={"supplierId": "a", "text": "x", "rating": 9}).status_code
    == 400,
)
fresh = next(i for i in client.get("/api/suppliers").json()["items"] if i["id"] == "a")
check("оценка команды в карточке", fresh["commentsRating"] == 4.5 and fresh["commentsCount"] == 2)
reputation = next(f for f in fresh["factors"] if f["id"] == "reputation")
check(
    "оценка команды в балле",
    any("коллеги оценили" in t for t in reputation["plus"]),
    reputation["plus"],
)
check(
    "чужой комментарий не удалить",
    other.delete(f"/api/comments/{posted['id']}").status_code == 404,
)
check("свой удаляется", client.delete(f"/api/comments/{posted['id']}").status_code == 200)

store.save_enrichment(
    "a",
    {"rating": 4.6, "reviews": 12, "reviews_source": "Zoon", "reviews_url": "https://zoon.ru/x/"},
)
for item in store.unscored(50):
    index.score_one(item)
with_reviews = next(i for i in client.get("/api/suppliers").json()["items"] if i["id"] == "a")
check("оценка справочника в карточке", with_reviews["reviewsSource"] == "Zoon")
rep_now = next(f for f in with_reviews["factors"] if f["id"] == "reputation")
check(
    "отзывы поднимают репутацию",
    rep_now["score"] > reputation["score"],
    (reputation["score"], rep_now["score"]),
)

client.post("/api/pipeline", json={"supplierId": "a", "status": "calling"})
calls = client.get("/api/calllist").json()
check(
    "обзвон: в работе те, кому звоним",
    [i["id"] for i in calls["working"]] == ["a"],
    calls["working"],
)
check("обзвон без отказов", all(i["id"] != "c" for i in calls["suggest"]))
check(
    "обзвон: кандидаты без статуса",
    all(i["status"] == "new" for i in calls["suggest"]),
    [(i["id"], i["status"]) for i in calls["suggest"]],
)
check(
    "обзвон только с контактами",
    all(i["phone"] or i["email"] for i in [*calls["working"], *calls["suggest"]]),
)
check(
    "обзвон: нумерация по приоритету",
    [i["rank"] for i in calls["suggest"]] == sorted(i["rank"] for i in calls["suggest"])
    and all(
        calls["suggest"][n]["score"] >= calls["suggest"][n + 1]["score"]
        for n in range(len(calls["suggest"]) - 1)
    ),
    [(i["rank"], i["score"]) for i in calls["suggest"]],
)
client.post("/api/pipeline", json={"supplierId": "a", "status": ""})

rec = client.post("/api/compare/recommend", json={"ids": ["a", "d"]}).json()
check("сравнение: лучший", rec["bestId"] == "a", rec.get("bestId"))

curated = client.post("/api/compare/recommend", json={"ids": ["t", "a", "x"]}).json()
check("сравнение: проверенный впереди", curated["bestId"] == "t", curated.get("bestId"))
check("сравнение: объяснение", len(rec["diff"]) > 0 and rec["diff"][0]["factor"])

csv_answer = client.get("/api/export.csv")
check("экспорт CSV", csv_answer.status_code == 200 and "Приоритет" in csv_answer.text[:200])
check(
    "админ без токена",
    client.post("/api/admin/verify", json={"supplierId": "d"}).status_code == 403,
)
check(
    "неизвестная категория -> 400",
    client.get("/api/suppliers", params={"category": "zzz"}).status_code == 400,
)
check(
    "неизвестный город -> 404",
    client.get("/api/suppliers", params={"city": "Атлантида"}).status_code == 404,
)

print()
print(f"{sum(ok)}/{len(ok)} проверок прошло")
sys.exit(0 if all(ok) else 1)
