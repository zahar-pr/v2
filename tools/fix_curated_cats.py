"""Чинит категории кураторских карточек.

Импортёр раскладывал компании по словам из описания, и часть попала не туда:
производители оборудования и систем автоматизации оказались в «овощах», а
масложировые заводы — в «заморозке». Для поиска поставщиков еды это шум.

    python3 tools/fix_curated_cats.py
"""

import os
import sys

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
)

import db
import index
import store
from db import _lock, connect

# Что это на самом деле: оборудование, ПО — не еда.
FIXES = {
    "Hurakan": ",equipment,",
    "Абат (Чувашторгтехника)": ",equipment,",
    "iiko": ",equipment,",
    "UCS (r_keeper)": ",equipment,",
    "SteadyControl HoReCa": ",equipment,",
    # масла и жиры — это ингредиенты, а не заморозка
    "Бунге СНГ": ",spices,",
    "Юг Руси": ",spices,",
    "НМЖК (Нижегородский масложировой комбинат)": ",spices,",
    "ЭФКО («Слобода»)": ",spices,",
}


def main() -> None:
    db.connect()
    changed = 0
    with _lock:
        connection = connect()
        for name, cats in FIXES.items():
            cursor = connection.execute(
                "UPDATE suppliers SET cats=? WHERE name=? AND trust_tier='trusted'", (cats, name)
            )
            changed += cursor.rowcount
        connection.commit()

    for name in FIXES:
        row = connection.execute(
            "SELECT * FROM suppliers WHERE name=? AND trust_tier='trusted'", (name,)
        ).fetchone()
        if row:
            index.score_one(store.row_to_dict(row))
    print(f"поправлено карточек: {changed}")


if __name__ == "__main__":
    main()
