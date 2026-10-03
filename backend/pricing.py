"""Дорогой поставщик или дешёвый — ответ до первого звонка.

Прайсы в открытых источниках почти никто не публикует: из 3600 поставщиков цену
на сайте называют единицы. Но уровень цены предсказывается структурой сделки, и
это знает любой закупщик: у завода берёшь дешевле, чем у дистрибьютора, а у
дистрибьютора дешевле, чем в мелкооптовой базе. Здесь это правило записано в код.

Важно: это оценка уровня, а не цена. Поэтому в карточке у неё всегда стоит
пометка «оценка» и перечислено, из чего она выведена, — чтобы закупщик понимал,
на что смотрит, и мог не согласиться.
"""

LOW = "low"
MID = "mid"
HIGH = "high"
CONTRACT = "contract"

TITLES = {
    LOW: "Ниже рынка",
    MID: "Средний уровень",
    HIGH: "Выше рынка",
    CONTRACT: "Цена по контракту",
}

HINTS = {
    LOW: "Отгрузка с производства без наценки посредника",
    MID: "Дистрибьюторская наценка к заводской цене",
    HIGH: "Мелкий опт и розница — самый дорогой вариант",
    CONTRACT: "Федеральный поставщик: цена считается под объём и сроки",
}

# Сколько «ступеней наценки» добавляет тип поставщика.
BY_TYPE = {
    "producer": (LOW, "прямой производитель — отгрузка с завода, без посредника"),
    "wholesale": (MID, "оптовая база или дистрибьютор — к заводской цене добавлена наценка"),
    "retail": (HIGH, "розничная точка — закупка по сути по розничной цене"),
    "unknown": (MID, "тип поставщика не определён, считаем по умолчанию как дистрибьютора"),
}

BULK_KG = 500  # с такого объёма разговор идёт уже о контрактной цене
SMALL_KG = 100  # мелкий опт: дешевле не будет

ORDER = (LOW, MID, HIGH)


def level(supplier: dict) -> dict:
    kind = supplier.get("kind_class") or "unknown"
    tier, reason = BY_TYPE.get(kind, BY_TYPE["unknown"])
    why = [reason]
    confidence = "mid" if kind != "unknown" else "low"

    moq = supplier.get("moq_value") or 0
    if moq >= BULK_KG:
        tier = _down(tier)
        why.append(f"минимальная партия от {_amount(moq)} — объём сам сбивает цену")
        confidence = "high"
    elif 0 < moq <= SMALL_KG:
        tier = _up(tier)
        why.append(f"мелкий опт от {_amount(moq)} — за такую партию просят дороже")
        confidence = "high"

    if (supplier.get("branches") or 1) > 3:
        tier = _up(tier)
        why.append(f"{supplier['branches']} точек в городе — это сеть торговли, а не производство")

    if supplier.get("own_delivery"):
        why.append("своя логистика: доставка обычно уже в цене")

    federal = _federal(supplier)
    if federal:
        tier = CONTRACT
        why.insert(0, federal)
        confidence = "mid"

    if supplier.get("price"):
        why.insert(0, f"в открытых источниках названа цена: {supplier['price']}")
        confidence = "high"
    elif supplier.get("price_list"):
        why.insert(0, "на сайте выложен прайс-лист — цену видно до звонка")
        confidence = "high"
    elif supplier.get("price_on_request"):
        why.append("сам поставщик пишет «цена по запросу»")

    return {
        "tier": tier,
        "title": TITLES[tier],
        "hint": HINTS[tier],
        "why": why,
        "confidence": confidence,
        "estimate": not (supplier.get("price") or supplier.get("price_list")),
    }


def _federal(supplier: dict) -> str:
    geo = (supplier.get("geo") or "").lower()
    if "вся рф" in geo or "всей росси" in geo or "по росси" in geo:
        return "возит по всей России — такие работают по годовым контрактам"
    if geo.count(",") >= 3:
        return "поставки больше чем в четыре региона — цена считается под контракт"
    if supplier.get("trust_tier") == "trusted" and (supplier.get("clients") or []):
        return "поставщик федеральных сетей — цена согласовывается под объём сети"
    return ""


def _down(tier: str) -> str:
    if tier not in ORDER:
        return tier
    return ORDER[max(0, ORDER.index(tier) - 1)]


def _up(tier: str) -> str:
    if tier not in ORDER:
        return tier
    return ORDER[min(len(ORDER) - 1, ORDER.index(tier) + 1)]


def _amount(value: float) -> str:
    if value >= 1000:
        return f"{value / 1000:.0f} т".replace(".0 ", " ")
    return f"{value:.0f} кг"
