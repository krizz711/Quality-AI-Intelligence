"""seed users

Revision ID: 20260528_seed_users
Revises: 20260528_create_users
Create Date: 2026-05-28 18:10:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260528_seed_users"
down_revision = "20260528_create_users"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            INSERT INTO users (id, username, hashed_password, role, created_at)
            VALUES
            ('88bfcab2-7dde-4de9-938a-b1f457b68845', 'admin', :admin_hash, 'admin', current_timestamp),
            ('151d6469-dfd7-45e7-a045-f67c905c42ad', 'quality_engineer', :eng_hash, 'quality_engineer', current_timestamp)
            ON CONFLICT (username) DO NOTHING;
            """
        ),
        {
            "admin_hash": "$2b$12$RJA.K1CLDZ9BER28jbpmhe8bgNFP0xcwInEu81sNj2ckSAD9Mlw9C",
            "eng_hash": "$2b$12$wEz9U18MOvVJguiiVM69peOIMMjy0NDJulcByMP0WTpjlulj6v2Fm",
        },
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            DELETE FROM users WHERE username IN ('admin', 'quality_engineer');
            """
        )
    )
