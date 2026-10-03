"""Пересчитывает балл, санитарное состояние, уровень цен и охват доставки для всей базы.

Нужен после правок формулы: колонки score_* и выводы хранятся в таблице, чтобы
по ним работали сортировка и фильтры, поэтому их надо обновить разом.

    python3 tools/rescore_all.py
"""

import os
import sys
import time

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
)

import db
import index
from db import _lock, connect


def main() -> None:
    db.connect()
    with _lock:
        connect().execute("UPDATE suppliers SET scored_at = 0")
        connect().commit()

    started = time.time()
    done = 0
    while True:
        pending = index.store.unscored(500)
        if not pending:
            break
        for row in pending:
            index.score_one(row)
        done += len(pending)
        print(f"  {done} пересчитано", flush=True)
    print(f"готово: {done} за {time.time() - started:.0f} с")


if __name__ == "__main__":
    main()
