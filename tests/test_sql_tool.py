from pathlib import Path

import pytest

from northstar_rag.sql_tool import execute_read_only, validate_read_only_sql


DATABASE = Path(__file__).resolve().parents[1] / "sample_data" / "northstar_rag_dummy_dataset" / "02_Attachments" / "support_operations.db"


def test_read_only_database_query():
    result = execute_read_only(DATABASE, "SELECT COUNT(*) AS total FROM open_service_requests")
    assert result.columns == ["total"]
    assert result.rows == [[60]]


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

