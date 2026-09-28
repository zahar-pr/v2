"""Убирает сведения из реестров, попавшие не тому поставщику.

Раньше «Прозрачный бизнес» и ЕГРЮЛ могли отдать тёзку из другого края: у «Хлебозавод 3»
из Казани оказывался ИНН ставропольского завода. Теперь сопоставление требует совпадения
региона, если в названии нет ничего своего, — а этот скрипт вычищает уже записанное
и возвращает карточки в очередь проверки.
"""

import os
import sys

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
)

import catalog
import domain
from db import connect

LEGAL_FIELDS = (
    "inn",
    "ogrn",
    "legal_name",
    "legal_status",
    "okved",
    "okved_name",
    "manager",
    "years",
    "founded",
)


def wrong_rows() -> list[tuple[str, str, str, str]]:
    codes = {city.name: city.code for city in catalog.CITIES}
    found = []
    for row in connect().execute(
        "SELECT id, name, city, inn FROM suppliers WHERE IFNULL(inn, '') != ''"
    ):
        code = codes.get(row["city"], "")
        if not code or domain.distinctive(row["name"]):
            continue
        if not domain.same_region(row["inn"], code):
            found.append((row["id"], row["name"], row["city"], row["inn"]))
    return found


def main() -> None:
    rows = wrong_rows()
    if not rows:
        print("Все ИНН совпадают с регионом города.")
        return

    connection = connect()
    fields = ", ".join(f"{name} = ''" for name in LEGAL_FIELDS if name != "founded")
    for supplier_id, name, city, inn in rows:
        connection.execute(
            f"UPDATE suppliers SET {fields}, founded = 0, legal_active = 1, "
            "fns_checked = 0, egrul_checked = 0, scored_at = 0 WHERE id = ?",
            (supplier_id,),
        )
        print(f"очищено: {name} ({city}) — ИНН {inn} из другого региона")
    connection.commit()
    print(f"\nвсего: {len(rows)}; карточки вернулись в очередь проверки реестров")


if __name__ == "__main__":
    main()
