"""002 add missing constraints

Revision ID: b83f256b0c45
Revises: 
Create Date: 2026-05-28 17:20:35.849093

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b83f256b0c45'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the base quality schema."""
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb")
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS measurements (
            id UUID NOT NULL DEFAULT gen_random_uuid(),
            timestamp TIMESTAMPTZ NOT NULL,
            part_number VARCHAR(64) NOT NULL,
            characteristic_name VARCHAR(128) NOT NULL,
            nominal_value DOUBLE PRECISION,
            measured_value DOUBLE PRECISION NOT NULL,
            unit VARCHAR(16),
            operator_id VARCHAR(64),
            equipment_id VARCHAR(64),
            shift VARCHAR(16),
            created_at TIMESTAMPTZ DEFAULT NOW(),
            created_by VARCHAR(64) DEFAULT 'system',
            PRIMARY KEY (id, timestamp)
        )
        """
    )
    op.execute("SELECT create_hypertable('measurements', 'timestamp', if_not_exists => TRUE)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS grr_studies (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            equipment_id VARCHAR(64) NOT NULL,
            characteristic_name VARCHAR(128) NOT NULL,
            status VARCHAR(32) DEFAULT 'pending',
            ev DOUBLE PRECISION,
            av DOUBLE PRECISION,
            pv DOUBLE PRECISION,
            grr_pct DOUBLE PRECISION,
            ndc INTEGER,
            operator_count INTEGER,
            part_count INTEGER,
            acceptance_decision VARCHAR(32),
            report_path TEXT,
            started_at TIMESTAMPTZ,
            completed_at TIMESTAMPTZ,
            reviewed_by VARCHAR(64),
            review_notes TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            created_by VARCHAR(64) DEFAULT 'system'
        )
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS quality_violations (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            timestamp TIMESTAMPTZ NOT NULL,
            part_number VARCHAR(64),
            characteristic_name VARCHAR(128),
            violation_type VARCHAR(64),
            severity VARCHAR(16),
            measured_value DOUBLE PRECISION,
            ucl DOUBLE PRECISION,
            lcl DOUBLE PRECISION,
            alert_sent BOOLEAN DEFAULT FALSE,
            acknowledged_by VARCHAR(64),
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS review_queue (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            study_id UUID NOT NULL REFERENCES grr_studies(id),
            status VARCHAR(32) DEFAULT 'pending',
            assigned_to VARCHAR(64),
            due_at TIMESTAMPTZ,
            decision_notes TEXT,
            decided_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_logs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            actor VARCHAR(128) NOT NULL,
            action VARCHAR(128) NOT NULL,
            entity_type VARCHAR(64) NOT NULL,
            entity_id VARCHAR(128) NOT NULL,
            details JSONB,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
        """
    )

    op.execute("CREATE INDEX IF NOT EXISTS idx_measurements_part_timestamp ON measurements (part_number, timestamp DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_measurements_equipment_id ON measurements (equipment_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_quality_violations_part_timestamp ON quality_violations (part_number, timestamp DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_review_queue_status ON review_queue (status)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_review_queue_study_id ON review_queue (study_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_entity_type_id_created_at ON audit_logs (entity_type, entity_id, created_at DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_actor_created_at ON audit_logs (actor, created_at DESC)")


def downgrade() -> None:
    """Drop the base quality schema."""
    op.execute("DROP TABLE IF EXISTS audit_logs")
    op.execute("DROP TABLE IF EXISTS review_queue")
    op.execute("DROP TABLE IF EXISTS quality_violations")
    op.execute("DROP TABLE IF EXISTS grr_studies")
    op.execute("DROP TABLE IF EXISTS measurements")
