"""Guards against the migration and scholium/store/schema.py drifting apart.

This is not a substitute for actually running the migration against Postgres
(see tests/store/test_store_live.py, marked `store`), but it catches the
common mistake of adding a table or column to one and forgetting the other,
without needing a database.
"""

from __future__ import annotations

import re
from pathlib import Path

from scholium.store.schema import ALL_TABLES

MIGRATION_PATH = (
    Path(__file__).resolve().parents[2] / "alembic" / "versions" / "97dcfeb6e8be_initial_schema.py"
)


def _migration_table_names() -> set[str]:
    text = MIGRATION_PATH.read_text(encoding="utf-8")
    return set(re.findall(r'op\.create_table\(\s*"([a-z_]+)"', text))


def test_every_schema_table_has_a_migration_create_table():
    schema_names = {table.name for table in ALL_TABLES}
    migration_names = _migration_table_names()
    assert schema_names == migration_names


def test_migration_creates_the_vector_extension():
    text = MIGRATION_PATH.read_text(encoding="utf-8")
    assert "CREATE EXTENSION IF NOT EXISTS vector" in text
