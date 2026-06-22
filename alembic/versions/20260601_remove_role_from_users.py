"""remove role from users

Revision ID: 20260601_remove_role_from_users
Revises: e9501605a8c2_add_alerts_and_notification_deliveries
Create Date: 2026-06-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20260601_remove_role_from_users'
down_revision = 'e9501605a8c2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    # Drop role column if exists
    try:
        op.drop_column('users', 'role')
    except Exception:
        # best-effort: ignore if already removed
        pass


def downgrade() -> None:
    # Re-create role column with default
    op.add_column('users', sa.Column('role', sa.String(length=32), nullable=False, server_default='quality_engineer'))
