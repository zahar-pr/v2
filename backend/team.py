import time

from db import _lock, connect


def notes_of() -> list[dict]:
    connection = connect()
    rows = connection.execute(
        "SELECT supplier_id, text, author, updated_at FROM notes WHERE text != '' "
        "ORDER BY updated_at DESC"
    ).fetchall()
    return [dict(row) for row in rows]


def save_note(user_id: str, author: str, supplier_id: str, text: str) -> dict:
    now = time.time()
    with _lock:
        connection = connect()
        connection.execute(
            "INSERT INTO notes (supplier_id, user_id, author, text, updated_at) "
            "VALUES (?, ?, ?, ?, ?) ON CONFLICT(supplier_id) DO UPDATE SET "
            "user_id=excluded.user_id, author=excluded.author, text=excluded.text, "
            "updated_at=excluded.updated_at",
            (supplier_id, user_id, author, text, now),
        )
        connection.commit()
    return {"supplier_id": supplier_id, "text": text, "author": author, "updated_at": now}


def delete_note(supplier_id: str) -> None:
    with _lock:
        connection = connect()
        connection.execute("DELETE FROM notes WHERE supplier_id=?", (supplier_id,))
        connection.commit()


def checks_of(supplier_id: str) -> list[str]:
    connection = connect()
    rows = connection.execute(
        "SELECT question FROM checks WHERE supplier_id=?", (supplier_id,)
    ).fetchall()
    return [row["question"] for row in rows]


def checks_count() -> dict:
    connection = connect()
    rows = connection.execute(
        "SELECT supplier_id, COUNT(*) AS n FROM checks GROUP BY supplier_id"
    ).fetchall()
    return {row["supplier_id"]: row["n"] for row in rows}


def set_check(supplier_id: str, question: str, done: bool, author: str) -> None:
    with _lock:
        connection = connect()
        if done:
            connection.execute(
                "INSERT INTO checks (supplier_id, question, author, updated_at) "
                "VALUES (?, ?, ?, ?) ON CONFLICT(supplier_id, question) DO UPDATE SET "
                "author=excluded.author, updated_at=excluded.updated_at",
                (supplier_id, question, author, time.time()),
            )
        else:
            connection.execute(
                "DELETE FROM checks WHERE supplier_id=? AND question=?", (supplier_id, question)
            )
        connection.commit()


def comments_of(supplier_id: str) -> list[dict]:
    connection = connect()
    rows = connection.execute(
        "SELECT * FROM comments WHERE supplier_id=? ORDER BY created_at DESC LIMIT 100",
        (supplier_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def comments_by(user_id: str, supplier_id: str) -> int:
    connection = connect()
    return connection.execute(
        "SELECT COUNT(*) FROM comments WHERE user_id=? AND supplier_id=?",
        (user_id, supplier_id),
    ).fetchone()[0]


def add_comment(user_id: str, supplier_id: str, author: str, text: str, rating) -> dict:
    now = time.time()
    with _lock:
        connection = connect()
        cursor = connection.execute(
            "INSERT INTO comments (supplier_id, user_id, author, text, rating, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (supplier_id, user_id, author, text, rating, now),
        )
        connection.commit()
        comment_id = cursor.lastrowid
    _refresh_comment_stats(supplier_id)
    return {
        "id": comment_id,
        "supplier_id": supplier_id,
        "user_id": user_id,
        "author": author,
        "text": text,
        "rating": rating,
        "created_at": now,
    }


def delete_comment(user_id: str, comment_id: int) -> str:
    with _lock:
        connection = connect()
        row = connection.execute(
            "SELECT supplier_id FROM comments WHERE id=? AND user_id=?", (comment_id, user_id)
        ).fetchone()
        if row is None:
            return ""
        connection.execute("DELETE FROM comments WHERE id=?", (comment_id,))
        connection.commit()
    _refresh_comment_stats(row["supplier_id"])
    return row["supplier_id"]


def _refresh_comment_stats(supplier_id: str) -> None:
    with _lock:
        connection = connect()
        row = connection.execute(
            "SELECT COUNT(*) AS n, AVG(rating) AS avg_rating FROM comments WHERE supplier_id=?",
            (supplier_id,),
        ).fetchone()
        connection.execute(
            "UPDATE suppliers SET comments_count=?, comments_rating=?, scored_at=0 WHERE id=?",
            (
                row["n"] or 0,
                round(row["avg_rating"], 1) if row["avg_rating"] else None,
                supplier_id,
            ),
        )
        connection.commit()


def profile_of(user_id: str) -> str:
    connection = connect()
    row = connection.execute("SELECT name FROM profiles WHERE user_id=?", (user_id,)).fetchone()
    return row["name"] if row else ""


def save_profile(user_id: str, name: str) -> str:
    with _lock:
        connection = connect()
        connection.execute(
            "INSERT INTO profiles (user_id, name, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET name=excluded.name, updated_at=excluded.updated_at",
            (user_id, name, time.time()),
        )
        connection.commit()
    return name


def statuses_of() -> dict:
    connection = connect()
    rows = connection.execute(
        "SELECT supplier_id, status, author, updated_at FROM pipeline"
    ).fetchall()
    return {
        row["supplier_id"]: {
            "status": row["status"],
            "author": row["author"],
            "updated_at": row["updated_at"],
        }
        for row in rows
    }


def set_status(user_id: str, author: str, supplier_id: str, status: str) -> dict:
    now = time.time()
    with _lock:
        connection = connect()
        if status in ("", "new"):
            connection.execute("DELETE FROM pipeline WHERE supplier_id=?", (supplier_id,))
        else:
            connection.execute(
                "INSERT INTO pipeline (supplier_id, user_id, author, status, updated_at) "
                "VALUES (?, ?, ?, ?, ?) ON CONFLICT(supplier_id) DO UPDATE SET "
                "user_id=excluded.user_id, author=excluded.author, status=excluded.status, "
                "updated_at=excluded.updated_at",
                (supplier_id, user_id, author, status, now),
            )
        connection.commit()
    return {"supplier_id": supplier_id, "status": status or "new", "updated_at": now}


def status_counts() -> dict:
    connection = connect()
    rows = connection.execute(
        "SELECT status, COUNT(*) AS n FROM pipeline GROUP BY status"
    ).fetchall()
    return {row["status"]: row["n"] for row in rows}
