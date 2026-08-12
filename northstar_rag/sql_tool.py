from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path


BLOCKED_SQL = re.compile(
    r"\b(insert|update|delete|drop|alter|create|replace|attach|detach|vacuum|reindex|pragma|load_extension)\b",
    re.IGNORECASE,
)


@dataclass
class QueryResult:
    columns: list[str]
    rows: list[list[object]]
    truncated: bool


def validate_read_only_sql(sql: str) -> str:
    cleaned = sql.strip()
    if not cleaned:
        raise ValueError("SQL is empty.")
    without_trailing = cleaned[:-1].strip() if cleaned.endswith(";") else cleaned
    if ";" in without_trailing:
        raise ValueError("Only one SQL statement is allowed.")
    if "--" in without_trailing or "/*" in without_trailing:
        raise ValueError("SQL comments are not allowed.")
    if not re.match(r"^(select|with)\b", without_trailing, re.IGNORECASE):
        raise ValueError("Only SELECT or WITH queries are allowed.")
    if BLOCKED_SQL.search(without_trailing):
        raise ValueError("The query contains a blocked SQL operation.")
    return without_trailing


def execute_read_only(database_path: Path, sql: str, max_rows: int = 200) -> QueryResult:
    statement = validate_read_only_sql(sql)
    uri = f"file:{database_path.resolve().as_posix()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True, timeout=2)
    try:
        steps = 0

        def progress() -> int:
            nonlocal steps
            steps += 1
            return 1 if steps > 50_000 else 0

        connection.set_progress_handler(progress, 1000)
        cursor = connection.execute(statement)
        columns = [item[0] for item in cursor.description or []]
        rows = cursor.fetchmany(max_rows + 1)
        return QueryResult(columns=columns, rows=[list(row) for row in rows[:max_rows]], truncated=len(rows) > max_rows)
    except sqlite3.Error as exc:
        raise ValueError(f"SQLite rejected the query: {exc}") from exc
    finally:
        connection.close()

