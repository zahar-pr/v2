"""Полное досье: что мы знаем, чего не знаем и где доглядеть остальное.

Главная претензия к сервису такого рода — прочерки в карточке. «Документы не
найдены» закупщик читает как «сервис не справился», и дальше идёт проверять
руками в десяток реестров.

Поэтому карточка устроена иначе. Всё, что удалось собрать, лежит в ней; всё, чего
собрать нельзя автоматически (декларации ТР ТС, проверки, суды, долги,
госконтракты), превращается в готовую ссылку с подставленным ИНН. Ни один пункт
не заканчивается тупиком: либо факт, либо точный адрес, где этот факт лежит.
"""

import time
from urllib.parse import quote

# Реестры, которые отвечают на вопросы закупщика. Порядок — от санитарии к деньгам.
REGISTRIES = (
    (
        "fsa",
        "Декларации и сертификаты (Росаккредитация)",
        "Есть ли действующая декларация ТР ТС на продукцию",
        "https://pub.fsa.gov.ru/rds/declaration?search={inn}",
        "https://pub.fsa.gov.ru/rds/declaration?search={name}",
    ),
    (
        "proverki",
        "Проверки надзора (ЕРКНМ)",
        "Какие проверки проходила компания и чем закончились",
        "https://proverki.gov.ru/portal/public-open-search?searchText={inn}",
        "https://proverki.gov.ru/portal/public-open-search?searchText={name}",
    ),
    (
        "mercury",
        "Ветеринарные документы (ФГИС «Меркурий»)",
        "Оформляет ли ветсертификаты на мясо, рыбу и молоко",
        "https://fsvps.gov.ru/ru/fsvps/importExport/search?q={inn}",
        "https://fsvps.gov.ru/ru/fsvps/importExport/search?q={name}",
    ),
    (
        "pb",
        "ФНС: Прозрачный бизнес",
        "Долги по налогам, массовый адрес, дисквалификация руководителя",
        "https://pb.nalog.ru/search.html?mode=search-all&queryAll={inn}",
        "https://pb.nalog.ru/search.html?mode=search-all&queryAll={name}",
    ),
    (
        "egrul",
        "Выписка из ЕГРЮЛ",
        "Официальная выписка с учредителями и видами деятельности",
        "https://egrul.nalog.ru/index.html?query={inn}",
        "https://egrul.nalog.ru/index.html?query={name}",
    ),
    (
        "arbitr",
        "Арбитражные дела",
        "Судится ли компания с покупателями и поставщиками",
        "https://kad.arbitr.ru/?q={inn}",
        "https://kad.arbitr.ru/?q={name}",
    ),
    (
        "fssp",
        "Исполнительные производства (ФССП)",
        "Есть ли непогашенные долги, взыскиваемые приставами",
        "https://fssp.gov.ru/iss/ip?is=1&var=1&inn={inn}",
        "https://fssp.gov.ru/iss/ip",
    ),
    (
        "zakupki",
        "Госконтракты",
        "Поставляет ли в школы и больницы — там требования жёстче наших",
        "https://zakupki.gov.ru/epz/supplier/search/results.html?searchString={inn}",
        "https://zakupki.gov.ru/epz/supplier/search/results.html?searchString={name}",
    ),
    (
        "rusprofile",
        "Выручка и связи (Rusprofile)",
        "Обороты по годам, совладельцы, связанные компании",
        "https://www.rusprofile.ru/search?query={inn}",
        "https://www.rusprofile.ru/search?query={name}",
    ),
)


def registries(supplier: dict) -> list[dict]:
    inn = (supplier.get("inn") or "").strip()
    name = quote((supplier.get("name") or "").strip())
    rows = []
    for key, title, why, by_inn, by_name in REGISTRIES:
        if inn:
            rows.append(
                {
                    "id": key,
                    "title": title,
                    "why": why,
                    "url": by_inn.format(inn=inn, name=name),
                    "byInn": True,
                }
            )
        else:
            rows.append(
                {
                    "id": key,
                    "title": title,
                    "why": why,
                    "url": by_name.format(inn=inn, name=name),
                    "byInn": False,
                }
            )
    return rows


# Поля карточки: подпись, где искать значение и почему это поле нужно закупщику.
PROFILE = (
    ("Телефон", lambda s: (s.get("phones") or [""])[0], "позвонить и услышать живого менеджера"),
    ("Почта", lambda s: (s.get("emails") or [""])[0], "отправить запрос КП письмом"),
    ("Сайт", lambda s: s.get("website"), "посмотреть ассортимент и прайс"),
    ("Адрес", lambda s: s.get("address"), "понять, откуда поедет машина"),
    ("Часы работы", lambda s: s.get("hours"), "знать, когда дозвониться"),
    ("ИНН", lambda s: s.get("inn"), "проверить компанию в реестрах"),
    ("ОГРН", lambda s: s.get("ogrn"), "сверить юрлицо в выписке"),
    ("Юрлицо", lambda s: s.get("legal_name"), "на кого оформлять договор"),
    ("Руководитель", lambda s: s.get("manager"), "кто подписывает договор"),
    ("Статус в ФНС", lambda s: s.get("legal_status"), "действует ли компания"),
    ("ОКВЭД", lambda s: s.get("okved"), "совпадает ли заявленная деятельность с едой"),
    ("Год регистрации", lambda s: s.get("founded"), "сколько лет компания на рынке"),
    ("Минимальный заказ", lambda s: s.get("moq"), "пройдём ли мы по объёму"),
    ("Цена", lambda s: s.get("price") or s.get("price_list"), "сравнить с текущим поставщиком"),
    ("Доставка", lambda s: s.get("delivery"), "кто везёт и за чей счёт"),
    ("География поставок", lambda s: s.get("geo"), "довезут ли до нашего города"),
    ("Документы", lambda s: ", ".join(s.get("certs") or []), "пройдёт ли проверку по качеству"),
    ("Описание", lambda s: s.get("about"), "чем компания занимается своими словами"),
    ("Оценка в справочниках", lambda s: s.get("reviews_source"), "что о ней пишут клиенты"),
)


def profile(supplier: dict) -> dict:
    known, missing = [], []
    for title, read, why in PROFILE:
        value = read(supplier)
        if value in (None, "", 0, []):
            missing.append({"title": title, "why": why})
        else:
            known.append({"title": title, "value": str(value)})
    total = len(PROFILE)
    return {
        "known": known,
        "missing": missing,
        "filled": len(known),
        "total": total,
        "percent": round(100 * len(known) / total),
    }


# Журнал проверок: что сервис уже сверил по этой компании и чем это кончилось.
# Пустое поле в карточке само по себе ничего не объясняет — закупщик не знает,
# то ли источник не смотрели, то ли смотрели и там действительно пусто. Разница
# принципиальная: в первом случае ждать, во втором сразу спрашивать у поставщика.
FOUND = "found"
EMPTY = "empty"
PENDING = "pending"


def audit(supplier: dict) -> list[dict]:
    rows = [
        _step(
            "Организации на карте",
            "OpenStreetMap: название, адрес, координаты, вид деятельности",
            supplier.get("checked_at"),
            bool(supplier.get("address") or supplier.get("lat")),
        ),
        _step(
            "ЕГРЮЛ",
            "Юрлицо, руководитель, ОГРН, запись о прекращении",
            supplier.get("egrul_checked"),
            bool(supplier.get("manager") or supplier.get("ogrn")),
        ),
        _step(
            "ФНС: Прозрачный бизнес",
            "ИНН, основной ОКВЭД, официальный статус организации",
            supplier.get("fns_checked"),
            bool(supplier.get("okved") or supplier.get("legal_status")),
        ),
        _step(
            "Сайт поставщика",
            "Контакты, условия отгрузки, документы на продукцию",
            supplier.get("enriched_at"),
            bool(supplier.get("about") or supplier.get("certs") or supplier.get("moq")),
            skipped=not supplier.get("website") and "сайт не найден, проверять нечего",
        ),
        _step(
            "Справочники отзывов",
            "Оценка и число отзывов по конкретной организации",
            supplier.get("reviews_checked"),
            bool(supplier.get("reviews_source")),
        ),
        # Санитарные перечни сверяются при каждой отдаче карточки, а не по расписанию:
        # список решений лежит в коде, сверка по ИНН и названию стоит микросекунды.
        _step(
            "Перечни санитарных решений",
            "Приостановки производства и массовые отравления",
            time.time(),
            True,
            note=_sanitary_note(supplier),
        ),
    ]
    return rows


def _sanitary_note(supplier: dict) -> str:
    state = (supplier.get("safety_state") or "").strip()
    if state in ("banned", "incident"):
        return "компания найдена в перечне — подробности выше"
    return "компания в перечне не числится"


def _step(
    title: str,
    what: str,
    moment,
    got: bool,
    skipped: str | bool = False,
    note: str = "",
) -> dict:
    if skipped:
        return {
            "title": title,
            "what": what,
            "state": EMPTY,
            "when": "",
            "note": skipped if isinstance(skipped, str) else "проверять нечего",
        }
    if not moment:
        return {
            "title": title,
            "what": what,
            "state": PENDING,
            "when": "",
            "note": "в очереди на проверку",
        }
    return {
        "title": title,
        "what": what,
        "state": FOUND if got else EMPTY,
        "when": _when(moment),
        "note": note or ("данные найдены" if got else "источник ответил, данных нет"),
    }


def _when(moment: float) -> str:
    days = int((time.time() - moment) // 86400)
    if days <= 0:
        return "сегодня"
    if days == 1:
        return "вчера"
    if days < 30:
        return f"{days} дн. назад"
    return time.strftime("%d.%m.%Y", time.localtime(moment))
