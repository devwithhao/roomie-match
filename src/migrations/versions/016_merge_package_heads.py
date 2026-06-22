"""merge package metadata and landlord package usage branches"""

from __future__ import annotations

from typing import Sequence, Union

revision: str = "016_merge_package_heads"
down_revision: Union[str, tuple[str, str], None] = ("015_timed_featured_posts", "4ec2a1c6449a")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
