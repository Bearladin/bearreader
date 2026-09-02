from typing import Optional

from pydantic import computed_field
import sqlmodel as sa

from ..enums import JobPriority, JobStatus, JobType, LanguageCode
from ._base import BaseTable
from ._enum import IntEnumType

_LANGUAGE_CODES = frozenset(LanguageCode)


class Job(BaseTable, table=True):
    __tablename__ = "jobs"  # type: ignore
    __table_args__ = (
        sa.Index("ix_jobs_is_done", "is_done"),
        sa.Index("ix_jobs_parent_job_id", "parent_job_id"),
        sa.Index("ix_jobs_depends_on", "depends_on", "is_done"),
        sa.Index("ix_jobs_scheduler", "status", "done", "type"),
        sa.Index("ix_jobs_ordering", "priority", "user_id", "updated_at"),
        sa.Index("ix_jobs_domain", "domain"),
    )

    user_id: str = sa.Field(foreign_key="users.id", ondelete="CASCADE")
    parent_job_id: Optional[str] = sa.Field(
        default=None,
        foreign_key="jobs.id",
        ondelete="CASCADE",
        nullable=True,
    )
    depends_on: Optional[str] = sa.Field(
        default=None,
        foreign_key="jobs.id",
        ondelete="CASCADE",
        nullable=True,
    )

    type: JobType = sa.Field(
        sa_column=sa.Column(IntEnumType(JobType), nullable=False),
        description="The job type",
    )
    domain: Optional[str] = sa.Field(
        default=None,
        nullable=True,
        description="Source domain for single-source crawl jobs; NULL = not throttled",
    )
    priority: JobPriority = sa.Field(
        default=JobPriority.LOW,
        sa_column=sa.Column(IntEnumType(JobPriority), nullable=False),
        description="The job priority",
    )
    status: JobStatus = sa.Field(
        default=JobStatus.PENDING,
        sa_column=sa.Column(IntEnumType(JobStatus), nullable=False),
        description="Current status",
    )
    is_done: bool = sa.Field(
        default=False, sa_type=sa.Boolean, description="Whether the job has completed"
    )
    error: Optional[str] = sa.Field(default=None, description="Error state in case of failure")
    started_at: Optional[int] = sa.Field(
        default=None, sa_type=sa.BigInteger, description="Job start time (UNIX ms)"
    )
    finished_at: Optional[int] = sa.Field(
        default=None, sa_type=sa.BigInteger, description="Job finish time (UNIX ms)"
    )

    done: int = sa.Field(default=0, description="Total completed items")
    failed: int = sa.Field(
        default=0,
        sa_column_kwargs={"server_default": sa.literal(0)},
        description="Total failed items",
    )
    total: int = sa.Field(default=1, description="Total items to complete")

    @computed_field  # type: ignore[misc]
    @property
    def is_running(self) -> int:
        """Whether the job is currently running"""
        return self.status == JobStatus.RUNNING

    @computed_field  # type: ignore[misc]
    @property
    def is_pending(self) -> int:
        """Whether the job is currently pending"""
        return self.status == JobStatus.PENDING

    @computed_field  # type: ignore[misc]
    @property
    def progress(self) -> int:
        """Progress percetage (value is between 0 to 100)"""
        return (100 * self.done) // self.total

    @computed_field  # type: ignore[misc]
    @property
    def job_title(self) -> str:
        if self.type == JobType.IMPORT_EPUB_ANALYZE:
            return f"分析 EPUB · {self.extra.get('original_name') or '本地书籍'}"

        if self.type == JobType.IMPORT_EPUB_COMMIT:
            title = self.extra.get("novel_title") or "本地书籍"
            return f"导入 EPUB · {title}"

        if self.type == JobType.IMPORT_TXT_ANALYZE:
            return f"分析 TXT · {self.extra.get('original_name') or '本地书籍'}"

        if self.type == JobType.IMPORT_TXT_COMMIT:
            title = self.extra.get("novel_title") or "本地书籍"
            return f"导入 TXT · {title}"

        # Require the URL only
        if self.type == JobType.NOVEL or self.type == JobType.FULL_NOVEL:
            return self.extra["url"]

        if self.type == JobType.NOVEL_BATCH or self.type == JobType.FULL_NOVEL_BATCH:
            urls = self.extra.get("urls") or []
            if len(urls) == 1:
                return urls[0]
            elif len(urls) > 1:
                return f"{urls[0]} 等 {len(urls)} 本小说"

        # Require the Novel Title
        novel_title = self.extra.get("novel_title") or ""
        if novel_title:
            novel_title = f'"{novel_title}" · '

        if self.type == JobType.VOLUME:
            volume_serial = self.extra.get("volume_serial") or ""
            if volume_serial:
                return f"{novel_title}第 {volume_serial} 卷"
            else:
                return f"{novel_title}分卷"

        if self.type == JobType.VOLUME_BATCH:
            ids = self.extra.get("volume_ids") or []
            return f"{novel_title}{len(ids)} 个分卷"

        if self.type == JobType.CHAPTER:
            chapter_serial = self.extra.get("chapter_serial")
            if chapter_serial:
                return f"{novel_title}第 {chapter_serial} 章"
            else:
                return f"{novel_title}章节"

        if self.type == JobType.CHAPTER_BATCH:
            ids = self.extra.get("chapter_ids") or []
            return f"{novel_title}{len(ids)} 个章节"

        if self.type == JobType.IMAGE:
            return self.extra.get("url") or f"{novel_title}图片"

        if self.type == JobType.IMAGE_BATCH:
            ids = self.extra.get("image_ids") or []
            return f"{novel_title}{len(ids)} 张图片"

        if self.type == JobType.ARTIFACT:
            format = self.extra.get("format") or "导出文件"
            return f"{novel_title}{format}"

        if self.type == JobType.ARTIFACT_BATCH:
            formats = self.extra.get("formats") or []
            if len(formats) <= 2:
                return f"{novel_title}{', '.join(formats)}"
            else:
                return f"{novel_title}{', '.join(formats[:2])} 等 {len(formats)} 种格式"

        if self.type == JobType.FETCH_MISSING:
            return f'补全缺失章节 · "{self.extra["novel_title"]}"'

        if self.type == JobType.FETCH_LATEST:
            return f'检查更新并补全 · "{self.extra["novel_title"]}"'

        if self.type == JobType.SEARCH_ALL_SOURCES:
            query = self.extra.get("query")
            return f"搜索「{query}」· 全部书源"

        if self.type == JobType.SEARCH_SOURCE:
            query = self.extra.get("query")
            domain = self.extra.get("domain")
            return f"搜索「{query}」· {domain}"

        # Require Language for translation
        language = self.extra.get("language") or ""
        if language in _LANGUAGE_CODES:
            language = f" → {language}"

        if self.type == JobType.NOVEL_TRANSLATION or self.type == JobType.FULL_NOVEL_TRANSLATION:
            return f"翻译 {novel_title[:-3]}{language}"

        if (
            self.type == JobType.NOVEL_TRANSLATION_BATCH
            or self.type == JobType.FULL_NOVEL_TRANSLATION_BATCH
        ):
            novel_ids = self.extra.get("novel_ids") or []
            return f"翻译 {len(novel_ids)} 本小说{language}"

        if self.type == JobType.VOLUME_TRANSLATION:
            volume_serial = self.extra.get("volume_serial") or ""
            if volume_serial:
                return f"翻译 {novel_title}第 {volume_serial} 卷{language}"
            else:
                return f"翻译 {novel_title}分卷{language}"

        if self.type == JobType.VOLUME_TRANSLATION_BATCH:
            ids = self.extra.get("volume_ids") or []
            return f"翻译 {novel_title}{len(ids)} 个分卷{language}"

        if self.type == JobType.CHAPTER_TRANSLATION:
            chapter_serial = self.extra.get("chapter_serial")
            if chapter_serial:
                return f"翻译 {novel_title}第 {chapter_serial} 章{language}"
            else:
                return f"翻译 {novel_title}章节{language}"

        if self.type == JobType.CHAPTER_TRANSLATION_BATCH:
            ids = self.extra.get("chapter_ids") or []
            return f"翻译 {novel_title}{len(ids)} 个章节{language}"

        return f"任务 {self.id}"
