"""timed featured posts

Revision ID: 015_timed_featured_posts
Revises: 014_package_usage_events
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "015_timed_featured_posts"
down_revision: Union[str, None] = "014_package_usage_events"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("posts", sa.Column("boosted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("posts", sa.Column("boost_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("idx_posts_boost_expires_at", "posts", ["boost_expires_at"])

    now = datetime.utcnow()
    op.execute(
        sa.text(
            "UPDATE posts SET boosted_at = :boosted_at, boost_expires_at = :boost_expires_at "
            "WHERE is_vip = :is_vip"
        ).bindparams(boosted_at=now, boost_expires_at=now + timedelta(days=3), is_vip=True)
    )

    packages = sa.table(
        "packages",
        sa.column("slug", sa.String),
        sa.column("features", sa.JSON),
    )
    conn = op.get_bind()
    durations = {"landlord-basic": 0, "landlord-pro": 3, "landlord-vip": 7}
    for slug, duration in durations.items():
        current = conn.execute(sa.select(packages.c.features).where(packages.c.slug == slug)).scalar_one_or_none()
        features = dict(current) if isinstance(current, dict) else {}
        features["boost_duration_days"] = duration
        conn.execute(packages.update().where(packages.c.slug == slug).values(features=features))


def downgrade() -> None:
    packages = sa.table(
        "packages",
        sa.column("slug", sa.String),
        sa.column("features", sa.JSON),
    )
    conn = op.get_bind()
    for slug in ("landlord-basic", "landlord-pro", "landlord-vip"):
        current = conn.execute(sa.select(packages.c.features).where(packages.c.slug == slug)).scalar_one_or_none()
        features = dict(current) if isinstance(current, dict) else {}
        features.pop("boost_duration_days", None)
        conn.execute(packages.update().where(packages.c.slug == slug).values(features=features))

    op.drop_index("idx_posts_boost_expires_at", table_name="posts")
    op.drop_column("posts", "boost_expires_at")
    op.drop_column("posts", "boosted_at")
