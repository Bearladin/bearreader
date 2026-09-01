"""Add indexes needed by EPUB import session cleanup

Revision ID: 0f7a8b9c0d1e
Revises: f82e926fe785
Create Date: 2026-09-01 14:58:00
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0f7a8b9c0d1e"
down_revision: Union[str, Sequence[str], None] = "f82e926fe785"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

try:
    dialect = op.get_context().dialect.name
except Exception:
    dialect = ""


def upgrade() -> None:
    """Upgrade schema."""
    # SQLite: indexes are created by the model-fingerprint sync path
    # (services/db.py _sync_sqlite_schema), same reason as f82e926fe785.
    if dialect == "sqlite":
        return
    op.create_index(
        "ix_import_sessions_expires_at",
        "import_sessions",
        ["expires_at"],
        unique=False,
    )
    op.create_index(
        "ix_import_sessions_file_sha256",
        "import_sessions",
        ["file_sha256"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    if dialect == "sqlite":
        return
    op.drop_index("ix_import_sessions_file_sha256", table_name="import_sessions")
    op.drop_index("ix_import_sessions_expires_at", table_name="import_sessions")
