"""add packages, purchases, entitlements tables

Revision ID: 007
Revises: 006_create_reviews_table
Create Date: 2024-05-18 10:00:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = "007_add_packages"
down_revision = "006_create_reviews_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    def table_exists(table_name: str) -> bool:
        return inspector.has_table(table_name)

    def index_exists(table_name: str, index_name: str) -> bool:
        if not table_exists(table_name):
            return False
        return any(index["name"] == index_name for index in inspector.get_indexes(table_name))

    # Create packages table
    if not table_exists("packages"):
        op.create_table(
            "packages",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("slug", sa.String(100), nullable=False, unique=True),
            sa.Column("name", sa.String(100), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("price_cents", sa.Integer(), nullable=False),
            sa.Column("currency", sa.String(10), nullable=False, server_default="vnd"),
            sa.Column("credits_match", sa.Integer(), nullable=True),
            sa.Column("credits_chatbot", sa.Integer(), nullable=True),
            sa.Column("period", sa.String(20), nullable=True),
            sa.Column("features", sa.JSON(), nullable=True),
            sa.Column("active", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.PrimaryKeyConstraint("id"),
        )
    if not index_exists("packages", "idx_packages_slug"):
        op.create_index("idx_packages_slug", "packages", ["slug"])

    # Create purchases table
    if not table_exists("purchases"):
        op.create_table(
            "purchases",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("account_id", sa.Integer(), nullable=False),
            sa.Column("package_id", sa.Integer(), nullable=False),
            sa.Column("provider", sa.String(50), nullable=False),
            sa.Column("provider_payment_id", sa.String(255), nullable=True),
            sa.Column("amount_cents", sa.Integer(), nullable=False),
            sa.Column("currency", sa.String(10), nullable=False, server_default="vnd"),
            sa.Column("status", sa.String(20), nullable=False),
            sa.Column("raw_payload", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                onupdate=sa.func.now(),
            ),
            sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], name="fk_purchases_account"),
            sa.ForeignKeyConstraint(["package_id"], ["packages.id"], name="fk_purchases_package"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("provider", "provider_payment_id", name="uq_provider_payment"),
        )
    if not index_exists("purchases", "idx_purchases_account"):
        op.create_index("idx_purchases_account", "purchases", ["account_id"])
    if not index_exists("purchases", "idx_purchases_status"):
        op.create_index("idx_purchases_status", "purchases", ["status"])

    # Create entitlements table
    if not table_exists("entitlements"):
        op.create_table(
            "entitlements",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("account_id", sa.Integer(), nullable=False),
            sa.Column("feature_key", sa.String(50), nullable=False),
            sa.Column("quantity", sa.Integer(), nullable=True),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("source_purchase_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                onupdate=sa.func.now(),
            ),
            sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], name="fk_entitlements_account"),
            sa.ForeignKeyConstraint(["source_purchase_id"], ["purchases.id"], name="fk_entitlements_purchase"),
            sa.PrimaryKeyConstraint("id"),
        )
    if not index_exists("entitlements", "idx_entitlements_account"):
        op.create_index("idx_entitlements_account", "entitlements", ["account_id"])
    if not index_exists("entitlements", "idx_entitlements_feature"):
        op.create_index("idx_entitlements_feature", "entitlements", ["account_id", "feature_key"])


def downgrade() -> None:
    op.drop_table("entitlements")
    op.drop_table("purchases")
    op.drop_table("packages")
