from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from northstar_rag.config import Settings
from northstar_rag.sql_tool import execute_read_only


parser = argparse.ArgumentParser(description="Run one validated read-only query against the demo SQLite database.")
parser.add_argument("sql", help="A single SELECT or WITH statement")
args = parser.parse_args()
database = Settings.from_env().data_dir / "02_Attachments" / "support_operations.db"
result = execute_read_only(database, args.sql)
print("\t".join(result.columns))
for row in result.rows:
    print("\t".join("" if value is None else str(value) for value in row))
if result.truncated:
    print("[truncated]", file=sys.stderr)

