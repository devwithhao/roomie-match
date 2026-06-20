"""add post content

Revision ID: 013_add_post_content
Revises: 012_package_target_role
Create Date: 2026-06-15

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "013_add_post_content"
down_revision: Union[str, None] = "012_package_target_role"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("posts", sa.Column("title", sa.String(length=255), nullable=True))
    op.add_column("posts", sa.Column("description", sa.Text(), nullable=True))

    bind = op.get_bind()
    dialect = bind.dialect.name
    if dialect in {"sqlite", "mysql", "mariadb"}:
        op.execute(
            """
            UPDATE posts
            SET title = (
                SELECT rooms.title FROM rooms WHERE rooms.id = posts.room_id
            ),
            description = (
                SELECT rooms.description FROM rooms WHERE rooms.id = posts.room_id
            )
            WHERE title IS NULL AND description IS NULL
            """
        )
    else:
        op.execute(
            """
            UPDATE posts
            SET title = rooms.title,
                description = rooms.description
            FROM rooms
            WHERE rooms.id = posts.room_id
              AND posts.title IS NULL
              AND posts.description IS NULL
            """
        )


def downgrade() -> None:
    op.drop_column("posts", "description")
    op.drop_column("posts", "title")
