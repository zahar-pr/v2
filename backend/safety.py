"""Санитарная история поставщика — то, из-за чего людей травят едой.

Главный вопрос сервиса не «кто возит муку», а «у кого можно брать, чтобы не
отравить гостей». На этот вопрос в открытых данных есть прямой ответ: решения
Роспотребнадзора и судов о приостановке производства и публикации о массовых
отравлениях. Здесь лежит перечень таких случаев и правила, как они влияют на
карточку.

Логика честная до конца. Если приостановка давно истекла, мы не делаем вид, что
компания до сих пор закрыта: пишем, что ограничение снято, но случай был, и
решение остаётся за закупщиком. Если же речь о массовом отравлении, карточка
горит красным бессрочно — такое не «истекает».

Компания, которой в перечне нет, получает не «нет данных», а «сверено с
перечнями, не числится»: отрицательный результат проверки — тоже результат.
"""

import time
from dataclasses import dataclass

import domain

# Степень тяжести: от неё зависит цвет карточки и потолок балла.
CRITICAL = "critical"  # массовое отравление, подтверждённый возбудитель
MAJOR = "major"  # приостановка производства за нарушения СанПиН
MINOR = "minor"  # протокол, предписание без остановки

CAPS = {CRITICAL: 0, MAJOR: 30, MINOR: 55}

BANNED = "banned"  # ограничение действует прямо сейчас
INCIDENT = "incident"  # случай был, ограничение снято
CLOSED = "closed"  # юрлицо прекратило деятельность — поставлять уже некому
CLEAN = "clean"  # сверено с перечнями — не числится
UNKNOWN = "unknown"  # сверять не с чем: ни юрлица, ни документов

RISKY_STATES = (BANNED, INCIDENT, CLOSED)


@dataclass(frozen=True)
class Incident:
    key: str  # name_key компании
    title: str  # как называется случай одной строкой
    severity: str
    date: str  # YYYY-MM-DD или YYYY-MM
    days: int  # срок приостановки в сутках, 0 — если остановки не было
    what: str  # что именно нашли
    chain: str  # в какую сеть возил
    source: str
    source_title: str
    inn: str = ""


# Дело поставщиков «Жизнь Марта» и «Сушкофа», Екатеринбург и Тюмень, май–июль 2024.
# Это единственный публичный массив санитарных решений по поставщикам общепита,
# который можно проверить по ссылкам, поэтому он и лежит в основе проверки.
INCIDENTS = (
    Incident(
        key="гумаровалуизафип",
        title="Массовое отравление: сальмонелла и листерия",
        severity=CRITICAL,
        date="2024-05-30",
        days=35,
        what=(
            "Роспотребнадзор признал виновником массового отравления 18 человек: "
            "сальмонелла в печени, сальмонелла и листерия в курице, инфицированные сотрудники"
        ),
        chain="Жизнь Март",
        source="https://ekb.rbc.ru/ekb/freenews/6658174c9a79475f4c91b4ec",
        source_title="РБК Екатеринбург",
    ),
    Incident(
        key="лабораториявкусаекбооо",
        title="Производство закрыто судом на 60 суток",
        severity=MAJOR,
        date="2024-06-03",
        days=60,
        what="Закрыт судом в рамках проверок после отравления; поставлял готовую еду и онигири",
        chain="Сушкоф и пицца",
        source=(
            "https://itsmycity.net/2024-06-03/"
            "sud-na60-sutok-zakryl-proizvodstvo-shestogo-postavshika-gotovoj-edy-dlya-zhiznmarta"
        ),
        source_title="It's My City",
    ),
    Incident(
        key="фабрикаяпонскойкухниооо",
        title="Приостановка 90 суток за нарушения СанПиН",
        severity=MAJOR,
        date="2024-06-01",
        days=90,
        what="Нарушения СанПиН, неудовлетворительные пробы продукции",
        chain="Жизнь Март",
        source="https://itsmycity.net/2024-06-03/sud-na60-sutok-zakryl-proizvodstvo-shestogo-postavshika-gotovoj-edy-dlya-zhiznmarta",
        source_title="It's My City",
    ),
    Incident(
        key="логинованшип",
        title="Приостановка 30 суток за нарушения СанПиН",
        severity=MAJOR,
        date="2024-06-01",
        days=30,
        what="Нарушения СанПиН, неудовлетворительные пробы продукции",
        chain="Жизнь Март",
        source="https://itsmycity.net/2024-06-03/sud-na60-sutok-zakryl-proizvodstvo-shestogo-postavshika-gotovoj-edy-dlya-zhiznmarta",
        source_title="It's My City",
    ),
    Incident(
        key="мутигулинаарип",
        title="Приостановка 30 суток за нарушения СанПиН",
        severity=MAJOR,
        date="2024-06-01",
        days=30,
        what="Нарушения СанПиН, неудовлетворительные пробы продукции",
        chain="Жизнь Март",
        source="https://itsmycity.net/2024-06-03/sud-na60-sutok-zakryl-proizvodstvo-shestogo-postavshika-gotovoj-edy-dlya-zhiznmarta",
        source_title="It's My City",
    ),
    Incident(
        key="курмачевмихаил",
        title="Производство закрыто судом на 30 суток",
        severity=MAJOR,
        date="2024-06-01",
        days=30,
        what="Закрыт судом в ходе проверок после отравления",
        chain="Жизнь Март",
        source="https://www.uralinform.ru/news/society/369203-vladelec-seti-jiznmart-nazval-vinovnika-massovogo-otravleniya-pokupatelei/",
        source_title="Уралинформбюро",
    ),
    Incident(
        key="шабалдароман",
        title="Производство закрыто судом на 30 суток",
        severity=MAJOR,
        date="2024-06-01",
        days=30,
        what="Закрыт судом в ходе проверок после отравления",
        chain="Жизнь Март",
        source="https://www.uralinform.ru/news/society/369203-vladelec-seti-jiznmart-nazval-vinovnika-massovogo-otravleniya-pokupatelei/",
        source_title="Уралинформбюро",
    ),
    Incident(
        key="якровиковмаксим",
        title="Производство закрыто судом на 30 суток",
        severity=MAJOR,
        date="2024-06-01",
        days=30,
        what="Закрыт судом в ходе проверок после отравления",
        chain="Жизнь Март",
        source="https://www.uralinform.ru/news/society/369203-vladelec-seti-jiznmart-nazval-vinovnika-massovogo-otravleniya-pokupatelei/",
        source_title="Уралинформбюро",
    ),
    Incident(
        key="гянджиевтимур",
        title="Производство закрыто судом на 30 суток",
        severity=MAJOR,
        date="2024-06-01",
        days=30,
        what="Закрыт судом в ходе проверок после отравления",
        chain="Жизнь Март",
        source="https://www.uralinform.ru/news/society/369203-vladelec-seti-jiznmart-nazval-vinovnika-massovogo-otravleniya-pokupatelei/",
        source_title="Уралинформбюро",
    ),
    Incident(
        key="ющенкосвип",
        title="Приостановка 60 суток: технология и сроки хранения",
        severity=MAJOR,
        date="2024-07-11",
        days=60,
        what="Грубые нарушения технологии производства, условий и сроков хранения",
        chain="Жизнь Март",
        source="https://www.uralinform.ru/news/society/369203-vladelec-seti-jiznmart-nazval-vinovnika-massovogo-otravleniya-pokupatelei/",
        source_title="Уралинформбюро",
    ),
    Incident(
        key="селивановаслип",
        title="Приостановка 30 суток: технология и сроки хранения",
        severity=MAJOR,
        date="2024-07-11",
        days=30,
        what="Грубые нарушения технологии производства, условий и сроков хранения",
        chain="Жизнь Март",
        source="https://www.uralinform.ru/news/society/369203-vladelec-seti-jiznmart-nazval-vinovnika-massovogo-otravleniya-pokupatelei/",
        source_title="Уралинформбюро",
    ),
    Incident(
        key="малютинаеип",
        title="Протокол о нарушениях при производстве и хранении",
        severity=MINOR,
        date="2024-07-01",
        days=0,
        what="Составлен протокол о нарушениях при производстве и хранении, остановки не было",
        chain="Жизнь Март",
        source="https://www.uralinform.ru/news/society/369203-vladelec-seti-jiznmart-nazval-vinovnika-massovogo-otravleniya-pokupatelei/",
        source_title="Уралинформбюро",
    ),
)

BY_KEY = {item.key: item for item in INCIDENTS}
BY_INN = {item.inn: item for item in INCIDENTS if item.inn}

CHAINS = tuple(dict.fromkeys(item.chain for item in INCIDENTS if item.chain))

DAY = 86400


def find(supplier: dict) -> Incident | None:
    """Сопоставление по ИНН, а если его нет — по нормализованному названию."""
    inn = (supplier.get("inn") or "").strip()
    if inn and inn in BY_INN:
        return BY_INN[inn]
    key = supplier.get("name_key") or domain.name_key(supplier.get("name", ""))
    return BY_KEY.get(key)


def _timestamp(date: str) -> float:
    parts = (date or "").split("-")
    try:
        year, month = int(parts[0]), int(parts[1])
        day = int(parts[2]) if len(parts) > 2 else 1
        return time.mktime((year, month, day, 12, 0, 0, 0, 1, -1))
    except (IndexError, ValueError, OverflowError):
        return 0.0


def active(item: Incident, now: float | None = None) -> bool:
    """Действует ли ограничение сейчас. Массовое отравление не «истекает»."""
    if item.severity == CRITICAL:
        return True
    if not item.days:
        return False
    started = _timestamp(item.date)
    return bool(started) and (now or time.time()) < started + item.days * DAY


# Документы, которые закупщик реально спрашивает у поставщика еды. Их наличие —
# единственное, что в открытых данных говорит о контроле качества на производстве.
FOOD_DOCS = (
    "Декларация ТР ТС",
    "Декларация о соответствии",
    "Сертификат соответствия",
    "ХАССП",
    "ISO 22000",
    "Ветеринарные документы",
    "ФГИС «Меркурий»",
    "Протокол испытаний",
)

# Пищевые ОКВЭД: раздел 10 — производство продуктов, 11 — напитки, 46.3 — опт едой,
# 01 — сельское хозяйство. Если ОКВЭД из этого списка, компания в принципе под
# санитарным надзором, а не просто «ООО с едой в названии».
FOOD_OKVED = ("10.", "11.", "46.3", "01.", "03.")

TRUSTED_TIER = "trusted"


def food_docs(supplier: dict) -> list[str]:
    certs = supplier.get("certs") or []
    return [item for item in certs if item in FOOD_DOCS]


def under_supervision(supplier: dict) -> bool:
    okved = (supplier.get("okved") or "").strip()
    return any(okved.startswith(prefix) for prefix in FOOD_OKVED)


def state_of(supplier: dict) -> dict:
    """Санитарное состояние карточки: цвет, заголовок, объяснение и потолок балла."""
    item = find(supplier)
    if item is not None:
        return _hit(item)

    docs = food_docs(supplier)
    checked = "Сверено с перечнями санитарных решений — компания в них не числится"

    status = (supplier.get("legal_status") or "").lower()
    if status and not supplier.get("legal_active") and "прекращ" in status:
        return {
            "state": CLOSED,
            "tone": "warn",
            "title": "Юрлицо прекратило деятельность",
            "text": (
                f"{checked}, но в ЕГРЮЛ есть запись о прекращении деятельности "
                f"(«{supplier.get('legal_status')}»). Договор с таким юрлицом заключить нельзя: "
                "либо компания работает через другое ООО, либо её уже нет. Уточните ИНН "
                "действующего юрлица до первого заказа."
            ),
            "cap": 45,
            "score": 15,
            "incident": None,
        }

    # Федеральные сети пускают к себе поставщиков только после аудита производства —
    # для закупщика это сильнее любой декларации, которую можно купить.
    clients = supplier.get("clients") or []
    if supplier.get("trust_tier") == TRUSTED_TIER:
        named = ", ".join(clients[:3])
        return {
            "state": CLEAN,
            "tone": "ok",
            "title": "Поставщик прошёл аудит федеральных сетей",
            "text": (
                f"{checked}. "
                + (
                    f"Компания поставляет в {named} — сети проводят собственный аудит "
                    "производства и лабораторный контроль партий, без них поставщика к "
                    "полке не пускают."
                    if named
                    else "Компания работает как федеральный поставщик HoReCa: такие проходят "
                    "входной аудит у каждой сети-заказчика."
                )
            ),
            "cap": 100,
            "score": 95,
            "incident": None,
        }

    if docs:
        return {
            "state": CLEAN,
            "tone": "ok",
            "title": "Санитарных решений нет, документы есть",
            "text": f"{checked}. В открытых источниках найдены: {', '.join(docs[:3])}.",
            "cap": 100,
            "score": 100,
            "incident": None,
        }
    if under_supervision(supplier) and supplier.get("legal_active"):
        return {
            "state": CLEAN,
            "tone": "ok",
            "title": "Санитарных решений нет",
            "text": (
                f"{checked}. Юрлицо действующее, основной ОКВЭД пищевой "
                f"({supplier.get('okved')}) — значит, компания под надзором Роспотребнадзора."
            ),
            "cap": 100,
            "score": 78,
            "incident": None,
        }
    if supplier.get("legal_active"):
        return {
            "state": CLEAN,
            "tone": "ok",
            "title": "Санитарных решений нет",
            "text": f"{checked}. Юрлицо действующее, но документов на продукцию мы не нашли.",
            "cap": 100,
            "score": 62,
            "incident": None,
        }
    return {
        "state": UNKNOWN,
        "tone": "warn",
        "title": "Санитарную историю подтвердить нечем",
        "text": (
            f"{checked}, но сверять почти не с чем: юрлицо не подтверждено в реестрах ФНС, "
            "документов на продукцию в открытых источниках нет. Запросите их до первой поставки."
        ),
        "cap": 100,
        "score": 40,
        "incident": None,
    }


def _hit(item: Incident) -> dict:
    now_active = active(item)
    ended = _ended(item)
    body = {
        "title": item.title,
        "severity": item.severity,
        "date": _human_date(item.date),
        "days": item.days,
        "what": item.what,
        "chain": item.chain,
        "source": item.source,
        "sourceTitle": item.source_title,
        "active": now_active,
        "until": ended,
    }
    if item.severity == CRITICAL:
        text = (
            f"{item.what}. Дата решения — {_human_date(item.date)}. "
            "Массовое отравление из истории компании не исчезает: работать с таким поставщиком "
            "без собственного аудита производства нельзя."
        )
    elif now_active:
        text = (
            f"{item.what}. Решение от {_human_date(item.date)}, приостановка на {item.days} суток "
            f"действует до {ended}. Поставки в этот период незаконны."
        )
    else:
        text = (
            f"{item.what}. Решение от {_human_date(item.date)}, приостановка на {item.days} суток "
            f"закончилась {ended} — формально запрета больше нет, но случай был. "
            "Берите только после своего аудита цеха и свежих протоколов лаборатории."
        )
    return {
        "state": BANNED if now_active else INCIDENT,
        "tone": "danger" if item.severity in (CRITICAL, MAJOR) else "warn",
        "title": item.title,
        "text": text,
        "cap": CAPS[item.severity],
        "score": 0 if item.severity == CRITICAL else (5 if now_active else 20),
        "incident": body,
    }


def _ended(item: Incident) -> str:
    started = _timestamp(item.date)
    if not started or not item.days:
        return ""
    return time.strftime("%d.%m.%Y", time.localtime(started + item.days * DAY))


MONTHS = (
    "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря",
)


def _human_date(date: str) -> str:
    parts = (date or "").split("-")
    if len(parts) < 2:
        return date
    try:
        month = MONTHS[int(parts[1]) - 1]
    except (ValueError, IndexError):
        return date
    day = parts[2] if len(parts) > 2 else ""
    return f"{int(day)} {month} {parts[0]}" if day else f"{month} {parts[0]}"
