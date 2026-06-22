"""add system_settings

Revision ID: 20260614b_system_settings
Revises: 20260614_gages_alert_rules
Create Date: 2026-06-14

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "20260614b_system_settings"
down_revision: Union[str, Sequence[str], None] = "20260614_gages_alert_rules"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS system_settings (
            key VARCHAR(128) PRIMARY KEY,
            value TEXT,
            is_secret BOOLEAN NOT NULL DEFAULT FALSE,
            updated_at TIMESTAMP,
            updated_by VARCHAR(128)
        );
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS system_settings")
