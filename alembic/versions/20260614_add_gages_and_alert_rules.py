"""add gages and alert_rules

Revision ID: 20260614_gages_alert_rules
Revises: 20260611_merge_heads
Create Date: 2026-06-14

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "20260614_gages_alert_rules"
down_revision: Union[str, Sequence[str], None] = "20260611_merge_heads"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS gages (
            id UUID PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            type VARCHAR(200) NOT NULL DEFAULT 'Inspection gage',
            nominal DOUBLE PRECISION,
            tolerance DOUBLE PRECISION,
            calibration_due VARCHAR(32),
            created_at TIMESTAMP
        );
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS alert_rules (
            id UUID PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            trigger VARCHAR(48) NOT NULL,
            threshold DOUBLE PRECISION,
            scope VARCHAR(200) NOT NULL DEFAULT 'Any process',
            channels JSON,
            enabled BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP
        );
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS alert_rules")
    op.execute("DROP TABLE IF EXISTS gages")
