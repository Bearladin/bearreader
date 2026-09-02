"""Add the source format to import sessions.

Revision ID: c4a7e2d98b31
Revises: 0f7a8b9c0d1e
Create Date: 2026-09-02 12:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "c4a7e2d98b31"
down_revision: Union[str, Sequence[str], None] = "0f7a8b9c0d1e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

try:
    dialect = op.get_context().dialect.name
except Exception:
    dialect = ""


def upgrade() -> None:
    """Upgrade schema."""
    # Existing SQLite databases are evolved by the additive model sync path.
    if dialect == "sqlite":
        return
    op.add_column(
        "import_sessions",
        sa.Column("source_format", sa.String(length=16), nullable=True),
    )
    op.execute(
        sa.text("UPDATE import_sessions SET source_format = 'epub' WHERE source_format IS NULL")
    )
    op.create_index(
        "ix_import_sessions_source_format",
        "import_sessions",
        ["source_format"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    if dialect == "sqlite":
        return
    op.drop_index(
        "ix_import_sessions_source_format",
        table_name="import_sessions",
    )
    op.drop_column("import_sessions", "source_format")
