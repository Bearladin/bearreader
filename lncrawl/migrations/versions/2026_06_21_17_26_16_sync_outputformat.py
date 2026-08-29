"""Sync OutputFormat

Revision ID: 7566560e767a
Revises: 3c313aa4605c
Create Date: 2026-06-21 17:26:16.711958
"""

from typing import Sequence, Union

from alembic import op

from lncrawl.enums import OutputFormat

# revision identifiers, used by Alembic.
revision: str = "7566560e767a"
down_revision: Union[str, Sequence[str], None] = "3c313aa4605c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

try:
    dialect = op.get_context().dialect.name
except Exception:
    dialect = ""


def upgrade() -> None:
    """Upgrade schema."""
    if dialect == "postgresql":
        names = ", ".join(f"'{m.name}'" for m in OutputFormat)
        op.execute("ALTER TABLE artifacts ALTER COLUMN format TYPE varchar USING format::varchar")
        op.execute("DROP TYPE outputformat")
        op.execute(f"CREATE TYPE outputformat AS ENUM ({names})")
        op.execute(
            "ALTER TABLE artifacts ALTER COLUMN format TYPE outputformat USING format::outputformat"
        )


def downgrade() -> None:
    """Downgrade schema."""
    upgrade()
