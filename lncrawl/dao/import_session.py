from typing import Any, Dict, Optional

import sqlmodel as sa

from ._base import BaseTable


class ImportSession(BaseTable, table=True):
    """Temporary state for a local book import before it becomes a novel."""

    __tablename__ = "import_sessions"  # type: ignore
    __table_args__ = (sa.Index("ix_import_sessions_user_status", "user_id", "status"),)

    user_id: str = sa.Field(
        foreign_key="users.id",
        ondelete="CASCADE",
        index=True,
    )
    analyze_job_id: Optional[str] = sa.Field(
        default=None,
        foreign_key="jobs.id",
        ondelete="SET NULL",
        nullable=True,
    )
    commit_job_id: Optional[str] = sa.Field(
        default=None,
        foreign_key="jobs.id",
        ondelete="SET NULL",
        nullable=True,
    )
    novel_id: Optional[str] = sa.Field(
        default=None,
        nullable=True,
    )
    file_sha256: str = sa.Field(index=True)
    source_format: Optional[str] = sa.Field(default=None, index=True)
    original_name: str
    file_size: int = sa.Field(sa_type=sa.BigInteger)
    staging_path: str
    status: str = sa.Field(index=True)
    error: Optional[str] = None
    preview: Dict[str, Any] = sa.Field(default_factory=dict, sa_type=sa.JSON)
    expires_at: int = sa.Field(sa_type=sa.BigInteger, index=True)
