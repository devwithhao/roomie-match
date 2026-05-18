"""add packages, purchases, entitlements tables

Revision ID: 006
Revises: 004_add_rental_history_table
Create Date: 2024-05-18 10:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "005_add_packages"
down_revision = "004_add_rental_history_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create packages table
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
    op.create_index("idx_packages_slug", "packages", ["slug"])

    # Create purchases table
    op.create_table(
        "purchases",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("account_id", sa.BigInteger(), nullable=False),  # Match accounts.id type
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
    op.create_index("idx_purchases_account", "purchases", ["account_id"])
    op.create_index("idx_purchases_status", "purchases", ["status"])

    # Create entitlements table
    op.create_table(
        "entitlements",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("account_id", sa.BigInteger(), nullable=False),  # Match accounts.id type
        sa.Column("feature_key", sa.String(50), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_purchase_id", sa.BigInteger(), nullable=True),
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
    op.create_index("idx_entitlements_account", "entitlements", ["account_id"])
    op.create_index("idx_entitlements_feature", "entitlements", ["account_id", "feature_key"])


def downgrade() -> None:
    op.drop_table("entitlements")
    op.drop_table("purchases")
    op.drop_table("packages")
