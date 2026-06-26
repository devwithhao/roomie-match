"""package usage events and landlord package standards

Revision ID: 014_package_usage_events
Revises: 013_add_post_content
Create Date: 2026-06-15

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "014_package_usage_events"
down_revision: Union[str, None] = "013_add_post_content"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


LANDLORD_PACKAGES = [
    {
        "id": 101,
        "slug": "landlord-basic",
        "name": "Landlord Basic",
        "description": "Goi co ban cho chu tro moi bat dau dang tin.",
        "price_cents": 49000,
        "features": {"posts_limit": 3, "photo_limit": 15, "boost_limit": 0},
    },
    {
        "id": 102,
        "slug": "landlord-pro",
        "name": "Landlord Pro",
        "description": "Tang hien thi va mo them luot day tin cho chu tro.",
        "price_cents": 199000,
        "features": {"posts_limit": 30, "photo_limit": 60, "boost_limit": 5},
    },
    {
        "id": 103,
        "slug": "landlord-vip",
        "name": "Landlord VIP",
        "description": "Uu tien hien thi cao nhat cho chu tro can phu tin manh.",
        "price_cents": 499000,
        "features": {"posts_limit": 100, "photo_limit": 150, "boost_limit": 20},
    },
]


def upgrade() -> None:
    op.create_table(
        "package_usage_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("feature_key", sa.String(length=50), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("entity_type", sa.String(length=50), nullable=True),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("source_purchase_id", sa.Integer(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], name="fk_package_usage_events_account"),
        sa.ForeignKeyConstraint(["source_purchase_id"], ["purchases.id"], name="fk_package_usage_events_purchase"),
    )
    op.create_index("idx_package_usage_events_account", "package_usage_events", ["account_id"])
    op.create_index("idx_package_usage_events_feature", "package_usage_events", ["feature_key"])
    op.create_index("idx_package_usage_events_entity", "package_usage_events", ["entity_type", "entity_id"])

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

    for item in LANDLORD_PACKAGES:
        op.execute(
            packages.update()
            .where(packages.c.slug == item["slug"])
            .values(
                name=item["name"],
                description=item["description"],
                price_cents=item["price_cents"],
                currency="vnd",
                target_role="landlord",
                credits_match=None,
                credits_chatbot=None,
                period="30_days",
                features=item["features"],
                active=True,
            )
        )

    existing_slugs = ", ".join(f"'{item['slug']}'" for item in LANDLORD_PACKAGES)
    conn = op.get_bind()
    rows = conn.execute(sa.text(f"SELECT slug FROM packages WHERE slug IN ({existing_slugs})")).fetchall()
    found = {row[0] for row in rows}
    missing = [item for item in LANDLORD_PACKAGES if item["slug"] not in found]
    if missing:
        op.bulk_insert(
            packages,
            [
                {
                    "slug": item["slug"],
                    "name": item["name"],
                    "description": item["description"],
                    "price_cents": item["price_cents"],
                    "currency": "vnd",
                    "target_role": "landlord",
                    "credits_match": None,
                    "credits_chatbot": None,
                    "period": "30_days",
                    "features": item["features"],
                    "active": True,
                }
                for item in missing
            ],
        )


def downgrade() -> None:
    op.drop_index("idx_package_usage_events_entity", table_name="package_usage_events")
    op.drop_index("idx_package_usage_events_feature", table_name="package_usage_events")
    op.drop_index("idx_package_usage_events_account", table_name="package_usage_events")
    op.drop_table("package_usage_events")
