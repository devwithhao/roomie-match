"""add room_code to rooms

Revision ID: 011_add_room_code
Revises: 010_add_suggested_accounts
Create Date: 2026-06-15

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "011_add_room_code"
down_revision: Union[str, None] = "010_add_suggested_accounts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("rooms", sa.Column("room_code", sa.String(length=30), nullable=True))
    op.execute("UPDATE rooms SET room_code = CONCAT('TRO-', LPAD(id, 6, '0')) WHERE room_code IS NULL")
    op.create_index("ix_rooms_room_code", "rooms", ["room_code"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_rooms_room_code", table_name="rooms")
    op.drop_column("rooms", "room_code")
