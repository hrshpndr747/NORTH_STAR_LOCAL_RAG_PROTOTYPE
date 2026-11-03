import sqlite3
from pathlib import Path

import pytest

from northstar_rag.sql_tool import execute_read_only, validate_read_only_sql


def test_read_only_database_query(tmp_path):
    db_file = tmp_path / "test.db"
    conn = sqlite3.connect(db_file)
    conn.execute("CREATE TABLE open_service_requests (id INTEGER)")
    conn.execute("INSERT INTO open_service_requests VALUES (60)")
    conn.commit()
    conn.close()
    result = execute_read_only(db_file, "SELECT COUNT(*) AS total FROM open_service_requests")
    assert result.columns == ["total"]
    assert result.rows == [[1]]


@pytest.mark.parametrize(
    "sql",
    [
        "DELETE FROM service_requests",
        "DROP TABLE service_requests",
        "PRAGMA table_info(service_requests)",
        "SELECT 1; SELECT 2",
        "SELECT 1 -- comment",
    ],
)
def test_database_writes_and_multiple_statements_are_blocked(sql):
    with pytest.raises(ValueError):
        validate_read_only_sql(sql)

