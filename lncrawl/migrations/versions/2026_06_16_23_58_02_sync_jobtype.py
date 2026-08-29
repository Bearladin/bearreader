"""Sync JobType

Revision ID: 3c313aa4605c
Revises: 527569d17dfc
Create Date: 2026-06-16 23:58:02.237829
"""

from typing import Sequence, Union

from alembic import op

from lncrawl.enums import JobType

# revision identifiers, used by Alembic.
revision: str = "3c313aa4605c"
down_revision: Union[str, Sequence[str], None] = "527569d17dfc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

try:
    dialect = op.get_context().dialect.name
except Exception:
    dialect = ""


def upgrade() -> None:
    """Upgrade schema."""
    if dialect == "postgresql":
        names = ", ".join(f"'{m.name}'" for m in JobType)
        op.execute("ALTER TABLE jobs ALTER COLUMN type TYPE varchar USING type::varchar")
        op.execute("DROP TYPE jobtype")
        op.execute(f"CREATE TYPE jobtype AS ENUM ({names})")
        op.execute("ALTER TABLE jobs ALTER COLUMN type TYPE jobtype USING type::jobtype")


def downgrade() -> None:
    """Downgrade schema."""
    upgrade()
