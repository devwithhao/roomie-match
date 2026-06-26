"""add package target role

Revision ID: 012_package_target_role
Revises: 011_add_room_code
Create Date: 2026-06-15

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "012_package_target_role"
down_revision: Union[str, None] = "011_add_room_code"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "packages",
        sa.Column("target_role", sa.String(length=20), nullable=False, server_default="tenant"),
    )
    op.create_index("idx_packages_target_role", "packages", ["target_role"])

    packages = sa.table(
        "packages",
        sa.column("id", sa.Integer),
        sa.column("slug", sa.String),
        sa.column("name", sa.String),
        sa.column("description", sa.Text),
        sa.column("price_cents", sa.Integer),
        sa.column("currency", sa.String),
        sa.column("target_role", sa.String),
        sa.column("credits_match", sa.Integer),
        sa.column("credits_chatbot", sa.Integer),
        sa.column("period", sa.String),
        sa.column("features", sa.JSON),
        sa.column("active", sa.Boolean),
    )

    op.bulk_insert(
        packages,
        [
            {
                "id": 101,
                "slug": "landlord-basic",
                "name": "Landlord Basic",
                "description": "Goi co ban cho chu tro moi bat dau dang tin.",
                "price_cents": 49000,
                "currency": "vnd",
                "target_role": "landlord",
                "credits_match": None,
                "credits_chatbot": None,
                "period": "30_days",
                "features": {"posts_limit": 3, "photo_limit": 15, "boost_limit": 0},
                "active": True,
            },
            {
                "id": 102,
                "slug": "landlord-pro",
                "name": "Landlord Pro",
                "description": "Tang hien thi va mo them luot day tin cho chu tro.",
                "price_cents": 199000,
                "currency": "vnd",
                "target_role": "landlord",
                "credits_match": None,
                "credits_chatbot": None,
                "period": "30_days",
                "features": {"posts_limit": 30, "photo_limit": 60, "boost_limit": 5},
                "active": True,
            },
            {
                "id": 103,
                "slug": "landlord-vip",
                "name": "Landlord VIP",
                "description": "Uu tien hien thi cao nhat cho chu tro can phu tin manh.",
                "price_cents": 499000,
                "currency": "vnd",
                "target_role": "landlord",
                "credits_match": None,
                "credits_chatbot": None,
                "period": "30_days",
                "features": {"posts_limit": 100, "photo_limit": 150, "boost_limit": 20},
                "active": True,
            },
        ],
    )


def downgrade() -> None:
    op.execute("DELETE FROM packages WHERE slug IN ('landlord-basic', 'landlord-pro', 'landlord-vip')")
    op.drop_index("idx_packages_target_role", table_name="packages")
    op.drop_column("packages", "target_role")
