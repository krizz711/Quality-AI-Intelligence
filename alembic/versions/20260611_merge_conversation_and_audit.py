"""merge conversation_sessions and audit_events heads

Revision ID: 20260611_merge_heads
Revises: 20260609_conversation, f0a1b2c3d4e5
Create Date: 2026-06-11
"""
from typing import Sequence, Union

revision: str = "20260611_merge_heads"
down_revision: Union[str, Sequence[str], None] = ("20260609_conversation", "f0a1b2c3d4e5")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
