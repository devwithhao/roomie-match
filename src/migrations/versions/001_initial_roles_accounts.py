"""initial roles and accounts tables with seed roles

Revision ID: 001_initial
Revises:
Create Date: 2026-05-04

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "roles",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            mysql.TIMESTAMP(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
        mysql_charset="utf8mb4",
        mysql_engine="InnoDB",
    )

    op.create_table(
        "accounts",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("username", sa.String(length=100), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column(
            "provider",
            sa.String(length=50),
            nullable=False,
            server_default=sa.text("'local'"),
        ),
        sa.Column("provider_id", sa.String(length=255), nullable=True),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'active'"),
        ),
        sa.Column(
            "email_verified",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("role_id", sa.BigInteger(), nullable=False),
        sa.Column("last_login_at", mysql.TIMESTAMP(), nullable=True),
        sa.Column(
            "created_at",
            mysql.TIMESTAMP(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            mysql.TIMESTAMP(),
            server_default=sa.text(
                "CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"
            ),
            nullable=False,
        ),
        sa.Column("deleted_at", mysql.TIMESTAMP(), nullable=True),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], name="fk_accounts_role"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("username"),
        mysql_charset="utf8mb4",
        mysql_engine="InnoDB",
    )

    roles_table = sa.table(
        "roles",
        sa.column("name", sa.String(length=50)),
        sa.column("description", sa.String(length=255)),
    )
    op.bulk_insert(
        roles_table,
        [
            {"name": "tenant", "description": "Nguoi thue tro"},
            {"name": "landlord", "description": "Chu tro"},
            {"name": "admin", "description": "Quan tri (no public API)"},
        ],
    )


def downgrade() -> None:
    op.drop_table("accounts")
    op.drop_table("roles")
