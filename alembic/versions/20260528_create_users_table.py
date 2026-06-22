"""create users table

Revision ID: 20260528_create_users
Revises: b83f256b0c45
Create Date: 2026-05-28 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from typing import Union, Sequence

# revision identifiers, used by Alembic.
revision = "20260528_create_users"
down_revision: Union[str, Sequence[str], None] = "b83f256b0c45"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Use IF NOT EXISTS to make this migration safe to rerun on partially provisioned DBs
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id UUID PRIMARY KEY,
            username VARCHAR(128) NOT NULL UNIQUE,
            hashed_password VARCHAR(256) NOT NULL,
            role VARCHAR(32) NOT NULL DEFAULT 'quality_engineer',
            created_at TIMESTAMP WITH TIME ZONE
        );
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS users")
