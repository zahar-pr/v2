import os
import random
import sys

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
)

import index
import store
import team

TEAM = (
    ("demo-irina", "Ирина Ковалёва"),
    ("demo-pavel", "Павел Дорошенко"),
    ("demo-artem", "Артём Гурский"),
    ("demo-svetlana", "Светлана Ким"),
    ("demo-dmitry", "Дмитрий Ушаков"),
)

NOTES = (
    "Ждём КП до 25.09, обещали прайс с отсрочкой 14 дней.",
    "Отгружают от паллеты, самовывоз со склада или их машина от 50 тысяч.",
    "Менеджер на связи с 8 до 17, после обеда перезванивает сам.",
    "Прислали декларацию ТР ТС, отдала на проверку качеству.",
    "Дорого по сравнению с текущим поставщиком, держим как запасной вариант.",
    "Готовы на тестовую поставку 200 кг без предоплаты.",
    "Просят предоплату 100% на первый заказ, торгуемся.",
    "Возят своим транспортом по области, в город каждый день.",
)

GOOD = (
    "Дозвонились с первого раза, прайс прислали в тот же день.",
    "Отгрузили в срок, качество ровное. Берём второй месяц подряд.",
    "Согласились на отсрочку 14 дней после второй поставки.",
    "Есть все документы, служба качества приняла без вопросов.",
    "Возят своим транспортом, довозят к открытию.",
    "Дали пробную партию бесплатно, по вкусу подошло.",
)
MIXED = (
    "Цена выше рынка, но берут малые объёмы без вопросов.",
    "Отвечают долго, зато условия нормальные.",
    "Менеджер меняется каждый месяц, приходится объяснять заново.",
    "Минимальный заказ великоват для нашей точки.",
)
BAD = (
    "Два раза сорвали срок, предупреждают постфактум.",
    "Прайс прислали только после третьего напоминания.",
    "Отказались работать по отсрочке, только предоплата.",
)

STATUS_PLAN = (
    ("fit", 9),
    ("quoted", 12),
    ("calling", 16),
    ("rejected", 7),
)


def pick(rows, count):

    return rows[:count], rows[count:]


def main():
    random.seed(20260919)
    defaults = store.best_defaults()
    rows, total, _ = store.search(
        region=defaults["region"],
        category=defaults["category"],
        kinds=("producer", "wholesale", "unknown"),
        per_page=40,
    )
    extra, _, _ = store.search(only_contacts=True, kinds=("producer", "wholesale"), per_page=60)
    wide = []
    for region in ("Москва и область", "Урал", "Сибирь", "Юг России", "Центральная Россия"):
        found, _, _ = store.search(
            region=region, only_contacts=True, kinds=("producer", "wholesale"), per_page=12
        )
        wide.extend(found)
    pool = list({row["id"]: row for row in [*rows, *extra, *wide]}.values())
    if not pool:
        print("индекс пуст, наполнять нечего")
        return

    touched = 0
    spread = list(pool)
    random.shuffle(spread)
    rest = spread
    for status, count in STATUS_PLAN:
        chosen, rest = pick(rest, count)
        for row in chosen:
            user, author = random.choice(TEAM)
            team.set_status(user, author, row["id"], status)
            touched += 1

    for row in pool[:3]:
        user, author = random.choice(TEAM)
        team.set_status(user, author, row["id"], random.choice(("calling", "quoted")))

    notes = 0
    for row in random.sample(pool, min(24, len(pool))):
        user, author = random.choice(TEAM)
        team.save_note(user, author, row["id"], random.choice(NOTES))
        notes += 1

    comments = 0
    for position, row in enumerate(pool[:45]):
        how_many = 3 if position < 14 else random.choice((1, 2, 2))
        used = set()
        for _ in range(how_many):
            user, author = random.choice(TEAM)
            if user in used:
                continue
            used.add(user)
            roll = random.random()
            if roll < 0.6:
                text, rating = random.choice(GOOD), random.choice((4, 5, 5))
            elif roll < 0.85:
                text, rating = random.choice(MIXED), random.choice((3, 4))
            else:
                text, rating = random.choice(BAD), random.choice((2, 3))
            team.add_comment(user, row["id"], author, text, rating)
            comments += 1

    checks = 0
    for row in pool[:28]:
        fresh = store.get(row["id"])
        if not fresh:
            continue
        questions = [
            question
            for factor in index.scoring.evaluate(index.scoring.with_age(fresh)).values()
            for question in factor["ask"]
        ]
        _, author = random.choice(TEAM)
        for question in questions[: random.choice((1, 2, 3))]:
            team.set_check(row["id"], question, True, author)
            checks += 1

    for row in pool:
        fresh = store.get(row["id"])
        if fresh:
            index.score_one(fresh)

    print(f"статусов: {touched}, заметок: {notes}, комментариев: {comments}, отметок: {checks}")
    print("счётчики по статусам:", team.status_counts())


main()
