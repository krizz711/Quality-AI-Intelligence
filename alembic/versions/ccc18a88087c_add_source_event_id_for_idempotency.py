"""add source_event_id for idempotency

Revision ID: ccc18a88087c
Revises: e9501605a8c2
Create Date: 2026-05-29 03:35:42.411576

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ccc18a88087c'
down_revision: Union[str, Sequence[str], None] = 'e9501605a8c2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
