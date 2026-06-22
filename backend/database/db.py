from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
DATABASE_PATH = DATA_DIR / "quality_control.db"
SCHEMA_PATH = Path(__file__).with_name("schema.sql")

TABLE_COLUMNS: dict[str, tuple[str, ...]] = {
    "grr_analyses": (
        "timestamp",
        "operators",
        "parts",
        "trials",
        "grr_percent",
        "repeatability_percent",
        "reproducibility_percent",
        "number_of_distinct_categories",
        "part_tolerance",
        "verdict",
        "ai_analysis",
        "raw_measurements",
    ),
    "spc_data": (
        "process_name",
        "timestamp",
        "measurement_value",
        "sample_mean",
        "ucl",
        "lcl",
        "centerline",
        "in_control",
        "violation_type",
    ),
    "alerts": (
        "type",
        "severity",
        "message",
        "process_name",
        "status",
        "created_at",
        "resolved_at",
        "resolved_by",
    ),
    "audit_log": (
        "timestamp",
        "event_type",
        "description",
        "user_id",
        "ip_address",
        "metadata",
    ),
}

JSON_COLUMNS = {
    "grr_analyses": {"raw_measurements"},
    "audit_log": {"metadata"},
}


def initialize_database(database_path: Path = DATABASE_PATH) -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(database_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    return database_path


def initialize_if_test_mode() -> None:
    """Initialize the on-disk SQLite DB only when running tests.

    This function is intentionally not executed at module import time.
    Tests or test fixtures can call it when they want the legacy SQLite
    database to be created for isolated test runs.
    """
    import os as _os

    if _os.environ.get("TEST_MODE", "").lower() == "true":
        initialize_database()


# Rollback / compatibility guard: some dev workflows expect the legacy
# SQLite database to be present at import time. To opt in temporarily set
# `LEGACY_DB_ENABLED=true` in the environment. This default is off so the
# application will not create SQLite files in production.
if __name__ != "__main__":
    try:
        import os as _os

        if _os.environ.get("LEGACY_DB_ENABLED", "").lower() == "true":
            initialize_database()
    except Exception:
        # Best-effort; do not crash the application if initialization fails
        pass


def get_test_db(tmp_path):
    """Factory for test fixtures — creates isolated SQLite DB."""
    test_db = tmp_path / "test_quality.db"
    initialize_database(test_db)
    return test_db


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return dict(row)


def _prepare_value(table_name: str, column_name: str, value: Any) -> Any:
    if column_name in JSON_COLUMNS.get(table_name, set()) and isinstance(value, (dict, list)):
        return json.dumps(value)
    if isinstance(value, bool):
        return int(value)
    return value


def _insert_row(table_name: str, data: dict[str, Any]) -> dict[str, Any]:
    allowed_columns = TABLE_COLUMNS[table_name]
    payload = {key: data[key] for key in allowed_columns if key in data}
    if not payload:
        raise ValueError(f"No insertable fields supplied for {table_name}")

    columns = ", ".join(payload.keys())
    placeholders = ", ".join(["?"] * len(payload))
    values = [_prepare_value(table_name, key, value) for key, value in payload.items()]

    with get_connection() as connection:
        cursor = connection.execute(
            f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})",
            values,
        )
        row_id = cursor.lastrowid

    inserted_row = find_by_id(table_name, row_id)
    if inserted_row is None:
        raise RuntimeError(f"Failed to fetch inserted row from {table_name}")
    return inserted_row


def _find_all_rows(table_name: str) -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            f"SELECT * FROM {table_name} ORDER BY id DESC"
        ).fetchall()
    return [dict(row) for row in rows]


def find_by_id(table_name: str, row_id: int) -> dict[str, Any] | None:
    with get_connection() as connection:
        row = connection.execute(
            f"SELECT * FROM {table_name} WHERE id = ?",
            (row_id,),
        ).fetchone()
    return _row_to_dict(row)


def _update_row(table_name: str, row_id: int, data: dict[str, Any]) -> dict[str, Any] | None:
    allowed_columns = TABLE_COLUMNS[table_name]
    payload = {
        key: data[key]
        for key in allowed_columns
        if key in data and key != "id"
    }
    if not payload:
        return find_by_id(table_name, row_id)

    assignments = ", ".join(f"{column} = ?" for column in payload)
    values = [_prepare_value(table_name, key, value) for key, value in payload.items()]
    values.append(row_id)

    with get_connection() as connection:
        connection.execute(
            f"UPDATE {table_name} SET {assignments} WHERE id = ?",
            values,
        )

    return find_by_id(table_name, row_id)


def insert_grr_analysis(data: dict[str, Any]) -> dict[str, Any]:
    return _insert_row("grr_analyses", data)


def find_all_grr_analyses() -> list[dict[str, Any]]:
    return _find_all_rows("grr_analyses")


def find_grr_analysis_by_id(row_id: int) -> dict[str, Any] | None:
    return find_by_id("grr_analyses", row_id)


def update_grr_analysis(row_id: int, data: dict[str, Any]) -> dict[str, Any] | None:
    return _update_row("grr_analyses", row_id, data)


def insert_spc_data(data: dict[str, Any]) -> dict[str, Any]:
    return _insert_row("spc_data", data)


def find_all_spc_data() -> list[dict[str, Any]]:
    return _find_all_rows("spc_data")


def find_spc_data_by_id(row_id: int) -> dict[str, Any] | None:
    return find_by_id("spc_data", row_id)


def update_spc_data(row_id: int, data: dict[str, Any]) -> dict[str, Any] | None:
    return _update_row("spc_data", row_id, data)


def insert_alert(data: dict[str, Any]) -> dict[str, Any]:
    return _insert_row("alerts", data)


def find_all_alerts() -> list[dict[str, Any]]:
    return _find_all_rows("alerts")


def find_alert_by_id(row_id: int) -> dict[str, Any] | None:
    return find_by_id("alerts", row_id)


def update_alert(row_id: int, data: dict[str, Any]) -> dict[str, Any] | None:
    return _update_row("alerts", row_id, data)


def insert_audit_log(data: dict[str, Any]) -> dict[str, Any]:
    return _insert_row("audit_log", data)


def find_all_audit_log() -> list[dict[str, Any]]:
    return _find_all_rows("audit_log")


def find_audit_log_by_id(row_id: int) -> dict[str, Any] | None:
    return find_by_id("audit_log", row_id)


def update_audit_log(row_id: int, data: dict[str, Any]) -> dict[str, Any] | None:
    return _update_row("audit_log", row_id, data)


__all__ = [
    "DATABASE_PATH",
    "find_all_alerts",
    "find_all_audit_log",
    "find_all_grr_analyses",
    "find_all_spc_data",
    "find_alert_by_id",
    "find_audit_log_by_id",
    "find_by_id",
    "find_grr_analysis_by_id",
    "find_spc_data_by_id",
    "get_connection",
    "initialize_database",
    "insert_alert",
    "insert_audit_log",
    "insert_grr_analysis",
    "insert_spc_data",
    "update_alert",
    "update_audit_log",
    "update_grr_analysis",
    "update_spc_data",
]