"""Drop feedback table

Feedback is now backed by the GitHub issue tracker instead of a local table.

Revision ID: f3b0a1c2d4e5
Revises: 7566560e767a
Create Date: 2026-06-21 18:30:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "f3b0a1c2d4e5"
down_revision: Union[str, Sequence[str], None] = "7566560e767a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "feedback" in inspector.get_table_names():
        op.drop_table("feedback")


def downgrade() -> None:
    """Downgrade schema."""
    # The feedback table is intentionally not recreated.
    pass
