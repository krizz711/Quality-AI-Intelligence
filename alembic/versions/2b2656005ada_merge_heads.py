"""merge_heads

Revision ID: 2b2656005ada
Revises: 20260601_remove_role_from_users, ccc18a88087c
Create Date: 2026-06-01 16:25:41.667694

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2b2656005ada'
down_revision: Union[str, Sequence[str], None] = ('20260601_remove_role_from_users', 'ccc18a88087c')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
