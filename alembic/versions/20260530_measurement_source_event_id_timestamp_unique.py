"""Enforce Timescale-safe measurement idempotency uniqueness.

Revision ID: 20260530_measurement_source_event_id_timestamp_unique
Revises: 20260529_measurement_event_id
Create Date: 2026-05-30 00:00:00.000000

"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260530_measurement_source_event_id_timestamp_unique"
down_revision: Union[str, Sequence[str], None] = "20260529_measurement_event_id"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE measurements DROP CONSTRAINT IF EXISTS uq_measurements_source_event_id")
    op.execute(
        "ALTER TABLE measurements ADD CONSTRAINT uq_measurements_source_event_id_timestamp "
        "UNIQUE (source_event_id, timestamp)"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE measurements DROP CONSTRAINT IF EXISTS uq_measurements_source_event_id_timestamp"
    )
    op.execute(
        "ALTER TABLE measurements ADD CONSTRAINT uq_measurements_source_event_id UNIQUE (source_event_id)"
    )