"""create audit_events table

Revision ID: f0a1b2c3d4e5
Revises: 2b2656005ada
Create Date: 2026-06-01 16:40:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f0a1b2c3d4e5'
down_revision = '2b2656005ada'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb")
    op.create_table(
        'audit_events',
        sa.Column('id', sa.UUID(), primary_key=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), primary_key=True),
        sa.Column('actor', sa.String(length=128), nullable=True),
        sa.Column('user_id', sa.String(length=128), nullable=True),
        sa.Column('event_type', sa.String(length=128), nullable=False),
        sa.Column('component', sa.String(length=128), nullable=True),
        sa.Column('input_hash', sa.String(length=128), nullable=True),
        sa.Column('algorithm_version', sa.String(length=64), nullable=True),
        sa.Column('result_summary', sa.JSON(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('ip_address', sa.String(length=64), nullable=True),
    )
    op.execute(
        "SELECT create_hypertable('audit_events', 'created_at', if_not_exists => TRUE, migrate_data => TRUE)"
    )
    op.execute(
        "SELECT add_retention_policy('audit_events', INTERVAL '7 years', if_not_exists => TRUE)"
    )


def downgrade() -> None:
    op.execute(
        """
        SELECT remove_retention_policy('audit_events', if_exists => TRUE)
        """
    )
    op.drop_table('audit_events')
