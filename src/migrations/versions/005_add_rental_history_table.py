"""add rental_history table

Revision ID: 005_add_rental_history_table
Revises: 004_add_profiles_table
Create Date: 2026-05-17

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision: str = "005_add_rental_history_table"
down_revision: Union[str, None] = "004_add_profiles_table"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "rental_history",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("account_id", sa.BigInteger(), nullable=False),
        sa.Column("room_id", sa.Integer(), nullable=False),
        sa.Column("post_id", sa.Integer(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'active'"),
        ),
        sa.Column(
            "created_at",
            mysql.TIMESTAMP(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.id"],
            name="fk_rental_history_account",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["room_id"],
            ["rooms.id"],
            name="fk_rental_history_room",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["post_id"],
            ["posts.id"],
            name="fk_rental_history_post",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        mysql_charset="utf8mb4",
        mysql_engine="InnoDB",
    )
    op.create_index(
        "ix_rental_history_account_id",
        "rental_history",
        ["account_id"],
        unique=False,
    )
    op.create_index(
        "ix_rental_history_status",
        "rental_history",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_rental_history_status", table_name="rental_history")
    op.drop_index("ix_rental_history_account_id", table_name="rental_history")
    op.drop_table("rental_history")
