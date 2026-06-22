"""add_alerts_and_notification_deliveries

Revision ID: e9501605a8c2
Revises: 20260530_measurement_source_event_id_timestamp_unique
Create Date: 2026-05-29 22:43:07.515562

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'e9501605a8c2'
down_revision: Union[str, Sequence[str], None] = '20260530_measurement_source_event_id_timestamp_unique'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    try:
        # Use SQL text with IF NOT EXISTS guards to make this migration idempotent
        op.execute(
            """
            CREATE TABLE IF NOT EXISTS alerts (
                id UUID PRIMARY KEY,
                type VARCHAR(32) NOT NULL,
                severity VARCHAR(16) NOT NULL,
                message TEXT NOT NULL,
                process_name VARCHAR(128) NOT NULL,
                status VARCHAR(16) NOT NULL DEFAULT 'active',
                metadata JSON,
                created_at TIMESTAMP,
                resolved_at TIMESTAMP WITH TIME ZONE,
                resolved_by VARCHAR(128)
            );
            """
        )

        op.execute(
            """
            CREATE TABLE IF NOT EXISTS notification_deliveries (
                id UUID PRIMARY KEY,
                alert_id UUID,
                channel VARCHAR(32) NOT NULL,
                status VARCHAR(32) NOT NULL,
                recipient VARCHAR(256),
                response_reference VARCHAR(128),
                error_message TEXT,
                created_at TIMESTAMP
            );
            """
        )

        op.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id UUID PRIMARY KEY,
                username VARCHAR(128) NOT NULL UNIQUE,
                hashed_password VARCHAR(256) NOT NULL,
                role VARCHAR(32) NOT NULL DEFAULT 'quality_engineer',
                created_at TIMESTAMP
            );
            """
        )

        op.execute(
            """
            CREATE TABLE IF NOT EXISTS alert_feedback (
                id UUID PRIMARY KEY,
                alert_id UUID NOT NULL,
                is_relevant BOOLEAN NOT NULL,
                category VARCHAR(64),
                notes TEXT,
                submitted_by VARCHAR(128) DEFAULT 'quality-engineer',
                created_at TIMESTAMP
            );
            """
        )

        op.execute("CREATE INDEX IF NOT EXISTS idx_alerts_alert_id ON alert_feedback (alert_id)")
    except Exception as e:
        if "already exists" in str(e).lower():
            # idempotent - object already exists
            pass
        else:
            raise


def downgrade() -> None:
    # Safe drop with IF EXISTS so downgrade is also idempotent
    op.execute("DROP TABLE IF EXISTS alert_feedback")
    op.execute("DROP TABLE IF EXISTS notification_deliveries")
    op.execute("DROP TABLE IF EXISTS alerts")
    op.execute("DROP TABLE IF EXISTS users")
