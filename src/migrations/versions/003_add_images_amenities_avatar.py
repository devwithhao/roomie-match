"""add room_images, amenities, room_amenities tables and avatar_url column

Revision ID: 003_add_images_amenities_avatar
Revises: 002_add_rooms_and_favorites
Create Date: 2026-05-11

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision: str = "003_add_images_amenities_avatar"
down_revision: Union[str, None] = "002_add_rooms_and_favorites"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "room_images",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("room_id", sa.Integer(), nullable=False),
        sa.Column("image_url", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["room_id"],
            ["rooms.id"],
            name="fk_room_images_room",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        mysql_charset="utf8mb4",
        mysql_engine="InnoDB",
    )

    op.create_table(
        "amenities",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        mysql_charset="utf8mb4",
        mysql_engine="InnoDB",
    )

    op.create_table(
        "room_amenities",
        sa.Column("room_id", sa.Integer(), nullable=False),
        sa.Column("amenity_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["room_id"],
            ["rooms.id"],
            name="fk_room_amenities_room",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["amenity_id"],
            ["amenities.id"],
            name="fk_room_amenities_amenity",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("room_id", "amenity_id"),
        mysql_charset="utf8mb4",
        mysql_engine="InnoDB",
    )

    op.add_column(
        "accounts",
        sa.Column("avatar_url", sa.String(length=500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("accounts", "avatar_url")
    op.drop_table("room_amenities")
    op.drop_table("amenities")
    op.drop_table("room_images")
