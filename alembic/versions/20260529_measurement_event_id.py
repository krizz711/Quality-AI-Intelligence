"""Add source_event_id to measurements for idempotency.

Revision ID: 20260529_measurement_event_id
Revises: 20260528_seed_users
Create Date: 2026-05-29 00:00:00.000000

"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260529_measurement_event_id"
down_revision: Union[str, Sequence[str], None] = "20260528_seed_users"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("measurements", sa.Column("source_event_id", sa.String(length=64), nullable=True))
    op.create_index("idx_measurements_source_event_id", "measurements", ["source_event_id"], unique=False)


def downgrade() -> None:
    # Use IF EXISTS style drops to be safe when rolling back on partially provisioned DBs
    op.execute("DROP INDEX IF EXISTS idx_measurements_source_event_id")
    op.execute("ALTER TABLE measurements DROP COLUMN IF EXISTS source_event_id")
