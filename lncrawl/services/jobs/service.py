from __future__ import annotations

from typing import Any, Callable, Dict, Iterable, List, Optional, TypeVar, Union

from sqlalchemy.orm import aliased
import sqlmodel as sq
from sqlmodel import Session

from ...context import ctx
from ...dao import (
    ActivityType,
    Job,
    JobPriority,
    JobStatus,
    JobType,
    LanguageCode,
    OutputFormat,
    User,
    UserRole,
)
from ...exceptions import ServerErrors
from ...server.models import Paginated
from ...utils.time_utils import current_timestamp
from .utils import select_ancestors, select_descendants

T = TypeVar("T")

# Job types that make HTTP requests to a single source domain in their own run().
# Only these are throttled to one running job per domain across the runner pool.
_DOMAIN_JOB_TYPES = frozenset(
    {
        JobType.NOVEL,
        JobType.FULL_NOVEL,
        JobType.CHAPTER,
        JobType.IMAGE,
        JobType.FETCH_MISSING,
        JobType.FETCH_LATEST,
        JobType.SEARCH_SOURCE,
    }
)
_INTERNAL_JOB_TYPES = frozenset(
    {
        JobType.IMPORT_EPUB_ANALYZE,
        JobType.IMPORT_EPUB_COMMIT,
        JobType.IMPORT_TXT_ANALYZE,
        JobType.IMPORT_TXT_COMMIT,
    }
)


class JobService:
    # -------------------------------------------------------------------------
    #                               GET Jobs
    # -------------------------------------------------------------------------
    def list(
        self,
        offset: int = 0,
        limit: int = 20,
        *,
        user_id: Optional[str] = None,
        job_type: Optional[JobType] = None,
        priority: Optional[JobPriority] = None,
        status: Optional[JobStatus] = None,
        is_done: Optional[bool] = None,
        parent_job_id: Optional[str] = None,
        include_internal: bool = False,
    ) -> Paginated[Job]:
        with ctx.db.session() as sess:
            stmt = sq.select(Job)
            cnt = sq.select(sq.func.count()).select_from(Job)

            # Apply filters
            conditions: List[Any] = []
            if user_id is not None:
                conditions.append(Job.user_id == user_id)
            if job_type is not None:
                conditions.append(Job.type == job_type)
            if status is not None:
                conditions.append(Job.status == status)
            if is_done is not None:
                conditions.append(sq.col(Job.is_done).is_(is_done))
            if priority is not None:
                conditions.append(Job.priority == priority)
            if parent_job_id is not None:
                conditions.append(Job.parent_job_id == parent_job_id)
            else:
                conditions.append(
                    sq.or_(
                        Job.status == JobStatus.PAUSED,
                        sq.col(Job.parent_job_id).is_(None),
                    )
                )
            if not include_internal:
                conditions.append(sq.col(Job.type).not_in(_INTERNAL_JOB_TYPES))

            if conditions:
                stmt = stmt.where(*conditions)
                cnt = cnt.where(*conditions)

            # Apply sorting
            if parent_job_id is not None:
                stmt = stmt.order_by(sq.asc(Job.created_at))
            else:
                stmt = stmt.order_by(sq.desc(Job.created_at))

            # Apply pagination
            stmt = stmt.offset(offset).limit(limit)

            total = sess.exec(cnt).one()
            items = sess.exec(stmt).all()
            self._decorate_search_summaries(sess, items)

            return Paginated(
                total=total,
                offset=offset,
                limit=limit,
                items=list(items),
            )

    def count(self) -> int:
        with ctx.db.session() as sess:
            return sess.scalar(sq.select(sq.func.count()).select_from(Job)) or 0

    def get(self, job_id: str) -> Job:
        with ctx.db.session() as sess:
            job = sess.get(Job, job_id)
            if not job:
                raise ServerErrors.no_such_job
            self._decorate_search_summaries(sess, [job])
            return job

    @staticmethod
    def _decorate_search_summaries(sess: Session, jobs: Iterable[Job]) -> None:
        """Attach live source-search counts without polluting progress totals.

        A search parent owns one scheduling unit and may also gain metadata jobs,
        so ``failed / total`` is not a truthful source count.  The response-only
        summary below is derived from direct SEARCH_SOURCE children instead.
        """
        search_parents = [job for job in jobs if job.type == JobType.SEARCH_ALL_SOURCES]
        if not search_parents:
            return
        parent_ids = [job.id for job in search_parents]
        children = sess.exec(
            sq.select(Job).where(
                sq.col(Job.parent_job_id).in_(parent_ids),
                Job.type == JobType.SEARCH_SOURCE,
            )
        ).all()
        by_parent: Dict[str, List[Job]] = {job_id: [] for job_id in parent_ids}
        for child in children:
            if child.parent_job_id in by_parent:
                by_parent[child.parent_job_id].append(child)
        for parent in search_parents:
            source_jobs = by_parent[parent.id]
            summary = {}
            for child in source_jobs:
                domain = str(child.extra.get("domain") or child.domain or child.id)
                search_completed = bool(child.extra.get("search_completed"))
                if child.status == JobStatus.PARTIAL or (search_completed and child.failed > 0):
                    state = "partial"
                elif child.status == JobStatus.FAILED:
                    state = "failed"
                elif search_completed or (
                    child.is_done and child.status in (JobStatus.SUCCESS, JobStatus.PARTIAL)
                ):
                    state = "completed"
                else:
                    state = "pending"
                summary[domain] = {
                    "state": state,
                    "result_count": int(child.extra.get("search_result_count") or 0),
                }
            parent.extra = {
                **parent.extra,
                "search_source_total": int(
                    parent.extra.get("search_source_total") or len(source_jobs)
                ),
                "search_sources": summary,
            }
            if parent.is_done and parent.status == JobStatus.SUCCESS:
                states = [source["state"] for source in summary.values()]
                if states and all(state == "failed" for state in states):
                    parent.status = JobStatus.FAILED
                elif parent.failed > 0 or any(state in ("failed", "partial") for state in states):
                    parent.status = JobStatus.PARTIAL

    def get_user_id(self, job_id: str) -> Optional[str]:
        with ctx.db.session() as sess:
            stmt = sq.select(Job.user_id).where(Job.id == job_id)
            return sess.exec(stmt).first()

    def verify_access(self, user: User, job_id: str) -> str:
        user_id = self.get_user_id(job_id)
        if not user_id:
            raise ServerErrors.no_such_job
        if user_id != user.id and user.role != UserRole.ADMIN:
            raise ServerErrors.forbidden
        return user_id

    def get_children_ids(self, parent_job_id: str) -> List[str]:
        with ctx.db.session() as sess:
            stmt = sq.select(Job.id).where(Job.parent_job_id == parent_job_id)
            return list(sess.exec(stmt).all())

    def get_children(self, parent_job_id: str) -> List[Job]:
        with ctx.db.session() as sess:
            stmt = sq.select(Job).where(Job.parent_job_id == parent_job_id)
            return list(sess.exec(stmt).all())

    def get_root_id(self, job_id: str) -> str:
        """沿 parent_job_id 向上找到根任务；自身无父级时返回自身 id。

        取消操作以根为对象：取消任何子任务意味着取消用户发起的整个请求。
        """
        with ctx.db.session() as sess:
            current = job_id
            while True:
                parent_id = sess.scalar(sq.select(Job.parent_job_id).where(Job.id == current))
                if parent_id is None:
                    return current
                current = parent_id

    def get_chapter_job(self, user_id: str, chapter_id: str) -> Optional[Job]:
        with ctx.db.session() as sess:
            return sess.exec(
                sq.select(Job)
                .where(
                    Job.user_id == user_id,
                    Job.type == JobType.CHAPTER,
                    sq.col(Job.parent_job_id).is_(None),
                    Job.extra["chapter_id"].as_string() == chapter_id,
                )
                .limit(1)
            ).first()

    def get_chapter_translation_job(
        self, user_id: str, chapter_id: str, language: LanguageCode
    ) -> Optional[Job]:
        with ctx.db.session() as sess:
            return sess.exec(
                sq.select(Job)
                .where(
                    Job.user_id == user_id,
                    Job.type == JobType.CHAPTER_TRANSLATION,
                    sq.col(Job.parent_job_id).is_(None),
                    Job.extra["chapter_id"].as_string() == chapter_id,
                    Job.extra["language"].as_string() == language,
                )
                .limit(1)
            ).first()

    def get_root(self, job_id: str) -> Optional[Job]:
        with ctx.db.session() as sess:
            return sess.scalar(
                sq.select(Job)
                .where(sq.col(Job.parent_job_id).is_(None))
                .where(sq.col(Job.id).in_(select_ancestors(job_id)))
                .limit(1)
            )

    # -------------------------------------------------------------------------
    #                              CREATE Jobs
    # -------------------------------------------------------------------------
    def fetch_novel(
        self,
        user: User,
        url: str,
        *,
        full: bool = False,
        parent_id: Optional[str] = None,
        depends_on: Optional[str] = None,
        **data: Any,
    ) -> Job:
        domain = ctx.sources.get_domain(url)
        ctx.sources.get_source(domain)  # validate
        data.update({"url": url})
        novel = ctx.novels.find_by_url(url)
        if novel:
            data["novel_id"] = novel.id
        return self._create(
            user=user,
            data=data,
            parent_id=parent_id,
            depends_on=depends_on,
            type=JobType.FULL_NOVEL if full else JobType.NOVEL,
        )

    def import_epub_analysis(
        self,
        user: User,
        session_id: str,
        original_name: str,
    ) -> Job:
        return self._create(
            user=user,
            data={
                "import_session_id": session_id,
                "original_name": original_name,
                "phase": "准备分析",
            },
            type=JobType.IMPORT_EPUB_ANALYZE,
            total=100,
        )

    def import_epub_commit(
        self,
        user: User,
        session_id: str,
        title: str,
        authors: str,
    ) -> Job:
        return self._create(
            user=user,
            data={
                "import_session_id": session_id,
                "novel_title": title,
                "authors": authors,
                "phase": "准备导入",
            },
            type=JobType.IMPORT_EPUB_COMMIT,
            total=100,
        )

    def import_txt_analysis(
        self,
        user: User,
        session_id: str,
        original_name: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> Job:
        return self._create(
            user=user,
            data={
                "import_session_id": session_id,
                "original_name": original_name,
                "source_format": "txt",
                "import_options": options or {},
                "phase": "准备分析",
            },
            type=JobType.IMPORT_TXT_ANALYZE,
            total=100,
        )

    def import_txt_commit(
        self,
        user: User,
        session_id: str,
        title: str,
        authors: str,
    ) -> Job:
        return self._create(
            user=user,
            data={
                "import_session_id": session_id,
                "novel_title": title,
                "authors": authors,
                "source_format": "txt",
                "phase": "准备导入",
            },
            type=JobType.IMPORT_TXT_COMMIT,
            total=100,
        )

    def fetch_many_novels(
        self,
        user: User,
        *urls: str,
        full: bool = False,
        parent_id: Optional[str] = None,
        depends_on: Optional[str] = None,
        **data: Any,
    ) -> Job:
        data.update({"urls": list(set(urls))})
        return self._create(
            user=user,
            data=data,
            parent_id=parent_id,
            depends_on=depends_on,
            type=JobType.FULL_NOVEL_BATCH if full else JobType.NOVEL_BATCH,
        )

    def fetch_volume(
        self,
        user: User,
        volume_id: str,
        *,
        parent_id: Optional[str] = None,
        depends_on: Optional[str] = None,
        **data: Any,
    ) -> Job:
        volume = ctx.volumes.get(volume_id)
        data.update(
            {
                "volume_id": volume_id,
                "volume_serial": volume.serial,
            }
        )
        if not data.get("novel_title"):
            novel = ctx.novels.get(volume.novel_id)
            data.update(
                {
                    "novel_id": novel.id,
                    "novel_title": novel.title,
                }
            )
        return self._create(
            user=user,
            data=data,
            parent_id=parent_id,
            depends_on=depends_on,
            type=JobType.VOLUME,
        )

    def fetch_many_volumes(
        self,
        user: User,
        *volume_ids: str,
        parent_id: Optional[str] = None,
        depends_on: Optional[str] = None,
        **data: Any,
    ) -> Job:
        first_volume = ctx.volumes.get(volume_ids[0])
        data.update(
            {
                "volume_ids": volume_ids,
            }
        )
        if not data.get("novel_title"):
            novel = ctx.novels.get(first_volume.novel_id)
            data.update(
                {
                    "novel_id": novel.id,
                    "novel_title": novel.title,
                }
            )
        return self._create(
            user=user,
            data=data,
            parent_id=parent_id,
            depends_on=depends_on,
            type=JobType.VOLUME_BATCH,
        )

    def fetch_chapter(
        self,
        user: User,
        chapter_id: str,
        *,
        parent_id: Optional[str] = None,
        depends_on: Optional[str] = None,
        **data: Any,
    ) -> Job:
        chapter = ctx.chapters.get(chapter_id)
        data.update(
            {
                "chapter_id": chapter_id,
                "chapter_serial": chapter.serial,
            }
        )
        if not data.get("novel_title"):
            novel = ctx.novels.get(chapter.novel_id)
            data.update(
                {
                    "novel_id": novel.id,
                    "novel_title": novel.title,
                }
            )
        return self._create(
            user=user,
            data=data,
            parent_id=parent_id,
            depends_on=depends_on,
            type=JobType.CHAPTER,
        )

    def fetch_many_chapters(
        self,
        user: User,
        *chapter_ids: str,
        parent_id: Optional[str] = None,
        depends_on: Optional[str] = None,
        **data: Any,
    ) -> Job:
        first_chapter = ctx.chapters.get(chapter_ids[0])
        data.update(
            {
                "chapter_ids": chapter_ids,
            }
        )
        if not data.get("novel_title"):
            novel = ctx.novels.get(first_chapter.novel_id)
            data.update(
                {
                    "novel_id": novel.id,
                    "novel_title": novel.title,
                }
            )
        return self._create(
            user=user,
            data=data,
            parent_id=parent_id,
            depends_on=depends_on,
            type=JobType.CHAPTER_BATCH,
        )

    def translate_chapter(
        self,
        user: User,
        chapter_id: str,
        language: LanguageCode,
        *,
        parent_id: Optional[str] = None,
        depends_on: Optional[str] = None,
        **data: Any,
    ) -> Job:
        chapter = ctx.chapters.get(chapter_id)
        data.update(
            {
                "chapter_id": chapter_id,
                "chapter_serial": chapter.serial,
                "language": language,
            }
        )
        if not data.get("novel_title"):
            novel = ctx.novels.get(chapter.novel_id)
            data.update(
                {
                    "novel_id": novel.id,
                    "novel_title": novel.title,
                }
            )
        return self._create(
            user=user,
            data=data,
            parent_id=parent_id,
            depends_on=depends_on,
            type=JobType.CHAPTER_TRANSLATION,
        )

    def translate_many_chapters(
        self,
        user: User,
        *chapter_ids: str,
        language: LanguageCode,
        parent_id: Optional[str] = None,
        depends_on: Optional[str] = None,
        **data: Any,
    ) -> Job:
        data.update(
            {
                "chapter_ids": list(chapter_ids),
                "language": language,
            }
        )
        return self._create(
            user=user,
            data=data,
            parent_id=parent_id,
            depends_on=depends_on,
            type=JobType.CHAPTER_TRANSLATION_BATCH,
        )

    def translate_novel(
        self,
        user: User,
        novel_id: str,
        language: LanguageCode,
        *,
        full: bool = False,
        parent_id: Optional[str] = None,
        depends_on: Optional[str] = None,
        **data: Any,
    ) -> Job:
        novel = ctx.novels.get(novel_id)
        data.update(
            {
                "novel_id": novel_id,
                "novel_title": novel.title,
                "language": language,
            }
        )
        return self._create(
            user=user,
            data=data,
            parent_id=parent_id,
            depends_on=depends_on,
            type=JobType.FULL_NOVEL_TRANSLATION if full else JobType.NOVEL_TRANSLATION,
        )

    def translate_many_novels(
        self,
        user: User,
        *novel_ids: str,
        language: LanguageCode,
        full: bool = False,
        parent_id: Optional[str] = None,
        depends_on: Optional[str] = None,
        **data: Any,
    ) -> Job:
        data.update(
            {
                "novel_ids": list(novel_ids),
                "language": language,
            }
        )
        return self._create(
            user=user,
            data=data,
            parent_id=parent_id,
            depends_on=depends_on,
            type=JobType.FULL_NOVEL_TRANSLATION_BATCH if full else JobType.NOVEL_TRANSLATION_BATCH,
        )

    def translate_volume(
        self,
        user: User,
        volume_id: str,
        language: LanguageCode,
        *,
        parent_id: Optional[str] = None,
        depends_on: Optional[str] = None,
        **data: Any,
    ) -> Job:
        volume = ctx.volumes.get(volume_id)
        data.update(
            {
                "volume_id": volume_id,
                "volume_serial": volume.serial,
                "language": language,
            }
        )
        if not data.get("novel_title"):
            novel = ctx.novels.get(volume.novel_id)
            data.update(
                {
                    "novel_id": novel.id,
                    "novel_title": novel.title,
                }
            )
        return self._create(
            user=user,
            data=data,
            parent_id=parent_id,
            depends_on=depends_on,
            type=JobType.VOLUME_TRANSLATION,
        )

    def translate_many_volumes(
        self,
        user: User,
        *volume_ids: str,
        language: LanguageCode,
        parent_id: Optional[str] = None,
        depends_on: Optional[str] = None,
        **data: Any,
    ) -> Job:
        data.update(
            {
                "volume_ids": list(volume_ids),
                "language": language,
            }
        )
        return self._create(
            user=user,
            data=data,
            parent_id=parent_id,
            depends_on=depends_on,
            type=JobType.VOLUME_TRANSLATION_BATCH,
        )

    def fetch_image(
        self,
        user: User,
        image_id: str,
        *,
        parent_id: Optional[str] = None,
        depends_on: Optional[str] = None,
        **data: Any,
    ) -> Job:
        image = ctx.images.get(image_id)
        data.update(
            {
                "image_id": image_id,
                "url": image.url,
            }
        )
        return self._create(
            user=user,
            data=data,
            parent_id=parent_id,
            depends_on=depends_on,
            type=JobType.IMAGE,
        )

    def fetch_many_images(
        self,
        user: User,
        *image_ids: str,
        parent_id: Optional[str] = None,
        depends_on: Optional[str] = None,
        **data: Any,
    ) -> Job:
        data.update(
            {
                "image_ids": image_ids,
            }
        )
        return self._create(
            user=user,
            data=data,
            parent_id=parent_id,
            depends_on=depends_on,
            type=JobType.IMAGE_BATCH,
        )

    def make_artifact(
        self,
        user: User,
        novel_id: str,
        format: OutputFormat,
        *,
        parent_id: Optional[str] = None,
        depends_on: Optional[str] = None,
        language: Optional[LanguageCode] = None,
        volume: Optional[int] = None,
        **data: Any,
    ) -> Job:
        data.update(
            {
                "novel_id": novel_id,
                "format": format,
                "language": language,
                "volume": volume,
            }
        )
        if not data.get("novel_title"):
            novel = ctx.novels.get(novel_id)
            data.update(
                {
                    "novel_title": novel.title,
                }
            )
        return self._create(
            user=user,
            data=data,
            parent_id=parent_id,
            depends_on=depends_on,
            type=JobType.ARTIFACT,
        )

    def make_many_artifacts(
        self,
        user: User,
        novel_id: str,
        *formats: OutputFormat,
        parent_id: Optional[str] = None,
        depends_on: Optional[str] = None,
        language: Optional[LanguageCode] = None,
        volume: Optional[int] = None,
        **data: Any,
    ) -> Job:
        data.update(
            {
                "novel_id": novel_id,
                "formats": formats,
                "language": language,
                "volume": volume,
            }
        )
        if not data.get("novel_title"):
            novel = ctx.novels.get(novel_id)
            data.update(
                {
                    "novel_title": novel.title,
                }
            )
        return self._create(
            user=user,
            data=data,
            parent_id=parent_id,
            depends_on=depends_on,
            type=JobType.ARTIFACT_BATCH,
        )

    def fetch_missing_chapters(
        self,
        user: User,
        novel_id: str,
        *,
        parent_id: Optional[str] = None,
        depends_on: Optional[str] = None,
        **data: Any,
    ) -> Job:
        novel = ctx.novels.get(novel_id)
        data.update(
            {
                "novel_id": novel_id,
                "novel_title": novel.title,
            }
        )
        return self._create(
            user=user,
            data=data,
            parent_id=parent_id,
            depends_on=depends_on,
            type=JobType.FETCH_MISSING,
        )

    def fetch_latest(
        self,
        user: User,
        novel_id: str,
        *,
        parent_id: Optional[str] = None,
        depends_on: Optional[str] = None,
        **data: Any,
    ) -> Job:
        novel = ctx.novels.get(novel_id)
        data.update(
            {
                "novel_id": novel_id,
                "novel_title": novel.title,
            }
        )
        return self._create(
            user=user,
            data=data,
            parent_id=parent_id,
            depends_on=depends_on,
            type=JobType.FETCH_LATEST,
        )

    def search_all_sources(
        self,
        user: User,
        query: str,
        *,
        parent_id: Optional[str] = None,
        depends_on: Optional[str] = None,
        **data: Any,
    ) -> Job:
        data["search_results"] = []
        data["query"] = str(query).strip().casefold()
        return self._create(
            user=user,
            data=data,
            parent_id=parent_id,
            depends_on=depends_on,
            type=JobType.SEARCH_ALL_SOURCES,
        )

    def search_single_source(
        self,
        user: User,
        query: str,
        domain: str,
        *,
        parent_id: Optional[str] = None,
        depends_on: Optional[str] = None,
        **data: Any,
    ) -> Job:
        data["domain"] = domain
        data["search_results"] = []
        data["query"] = str(query).strip().casefold()
        source = ctx.sources.get_source(domain)
        if not source.can_search:
            raise ServerErrors.search_not_supported.with_extra(domain)
        data["url"] = source.url
        return self._create(
            user=user,
            data=data,
            parent_id=parent_id,
            depends_on=depends_on,
            type=JobType.SEARCH_SOURCE,
        )

    # -------------------------------------------------------------------------
    #                              DELETE Jobs
    # -------------------------------------------------------------------------
    def delete(self, job_id: str) -> None:
        """Delete a finished ROOT job and its descendants (idempotent).

        Unfinished jobs (pending/running/paused, is_done=false) are refused;
        deleting a child job directly is refused too. Related business data
        (novels, artifacts, files) is untouched — artifacts keep their rows
        with job_id set to NULL per the FK rule.
        """
        with ctx.db.session() as sess:
            result = sess.exec(sq.select(Job).where(Job.id == job_id)).first()
            if not result:
                return  # idempotent: deleting a missing job succeeds
            done, total, failed = result.done, result.total, result.failed
            if result.parent_job_id is not None:
                raise ServerErrors.cannot_delete_child_job.with_extra(job_id)
            if not result.is_done:
                raise ServerErrors.cannot_delete_running_job.with_extra(job_id)

            self._update_up(
                sess,
                job_id=job_id,
                done=Job.done - done,
                total=Job.total - total,
                failed=Job.failed - failed,
            )

            sa_deps = select_descendants(job_id, True)
            sess.exec(sq.delete(Job).where(sq.col(Job.id).in_(sa_deps)))

            sess.commit()

    def delete_finished(self) -> None:
        """Delete every finished root job (and descendants) in one transaction.

        Waiting/running/paused jobs are never touched. Returns nothing — the
        caller must not depend on a deleted count.
        """
        with ctx.db.session() as sess:
            roots = sess.exec(
                sq.select(Job).where(
                    Job.parent_job_id.is_(None),  # type: ignore[union-attr]
                    Job.is_done.is_(True),  # type: ignore[union-attr]
                )
            ).all()
            for job in roots:
                self._update_up(
                    sess,
                    job_id=job.id,
                    done=Job.done - job.done,
                    total=Job.total - job.total,
                    failed=Job.failed - job.failed,
                )
                sa_deps = select_descendants(job.id, True)
                sess.exec(sq.delete(Job).where(sq.col(Job.id).in_(sa_deps)))
            sess.commit()

    # -------------------------------------------------------------------------
    #                              CANCEL Jobs
    # -------------------------------------------------------------------------

    def cancel(self, job_id: str) -> None:
        with ctx.db.session() as sess:
            job = sess.get(Job, job_id)
            if job is None or job.is_done:
                return
            result = sess.exec(
                sq.update(Job)
                .where(
                    sq.col(Job.id) == job_id,
                    sq.col(Job.is_done).is_(False),
                )
                .values(
                    is_done=True,
                    status=JobStatus.CANCELED,
                    error="任务已取消",
                    started_at=sq.func.coalesce(Job.started_at, current_timestamp()),
                    finished_at=current_timestamp(),
                )
            )
            if result.rowcount != 1:
                return
            self._cancel_down(sess, job_id, False)
            sess.commit()

    def cancel_active_for_shutdown(self) -> int:
        """Persist cancellation for every queued/running desktop job.

        Worker signals are set before this method is called.  Marking the rows
        here prevents a quick relaunch from reclaiming work that the user
        explicitly abandoned by closing the desktop application.
        """
        now = current_timestamp()
        with ctx.db.session() as sess:
            result = sess.exec(
                sq.update(Job)
                .where(sq.col(Job.is_done).is_(False))
                .values(
                    is_done=True,
                    status=JobStatus.CANCELED,
                    error="程序关闭，任务已取消",
                    started_at=sq.func.coalesce(Job.started_at, now),
                    finished_at=sq.func.coalesce(Job.finished_at, now),
                )
            )
            sess.commit()
            return int(result.rowcount or 0)

    # -------------------------------------------------------------------------
    #                            Internal Methods
    # -------------------------------------------------------------------------
    def _get_active_job_count(
        self,
        sess: Session,
        user_id: str,
        types: Optional[List[JobType]] = None,
    ):
        stmt = sq.select(sq.func.count())
        stmt = stmt.select_from(Job)
        stmt = stmt.where(
            Job.user_id == user_id,
            sq.col(Job.is_done).is_(False),
            sq.col(Job.parent_job_id).is_(None),
        )
        if types:
            stmt = stmt.where(sq.col(Job.type).in_(types))
        return sess.scalar(stmt) or 0

    def _ensure_user_access_limit(self, sess: Session, user: User):
        limit = ctx.tier.max_active_jobs(user)
        if limit is not None:
            active = self._get_active_job_count(sess, user.id)
            if active >= limit:
                raise ServerErrors.job_limit_reached.with_extra(active)

        search_limit = ctx.tier.max_active_search_jobs(user)
        if search_limit is not None:
            active = self._get_active_job_count(
                sess,
                user.id,
                types=[
                    JobType.SEARCH_SOURCE,
                    JobType.SEARCH_ALL_SOURCES,
                ],
            )
            if active >= search_limit:
                raise ServerErrors.search_job_limit_reached.with_extra(active)

    def _resolve_domain(self, type: JobType, data: dict) -> Optional[str]:
        """Resolve the single source domain for throttled crawl jobs (else None)."""
        if type not in _DOMAIN_JOB_TYPES:
            return None
        try:
            domain = data.get("domain")
            if domain:
                return domain
            url = data.get("url")
            if url:
                return ctx.sources.get_domain(url)
            novel_id = data.get("novel_id")
            if not novel_id and data.get("chapter_id"):
                novel_id = ctx.chapters.get(data["chapter_id"]).novel_id
            if novel_id:
                return ctx.novels.get(novel_id).domain
        except Exception:
            return None
        return None

    def _create(
        self,
        user: User,
        type: JobType,
        data: dict,
        parent_id: Optional[str] = None,
        depends_on: Optional[str] = None,
        total: int = 1,
    ) -> Job:
        if total < 1:
            raise ValueError("Job total must be positive")
        with ctx.db.session() as sess:
            if parent_id is None:
                self._ensure_user_access_limit(sess, user)

            job = Job(
                type=type,
                extra=data,
                user_id=user.id,
                depends_on=depends_on,
                parent_job_id=parent_id,
                priority=ctx.tier.job_priority(user),
                domain=self._resolve_domain(type, data),
                total=total,
            )
            sess.add(job)

            self._update_up(
                sess,
                job.id,
                total=Job.total + total,
            )

            sess.commit()
            sess.refresh(job)

        if parent_id is None:
            ctx.activity.record(user.id, ActivityType.REQUEST, job.id)
        return job

    def _pending(
        self,
        artifact: Optional[bool] = None,
        skip_job_ids: Iterable[str] = [],
        skip_user_ids: Iterable[str] = [],
        skip_domains: Iterable[str] = [],
    ) -> Optional[Job]:
        with ctx.db.session() as sess:
            stmt = sq.select(Job)

            job_alias = aliased(Job)
            dep_is_done = (
                sq.exists(1)
                .where(sq.col(job_alias.id) == Job.depends_on)
                .where(sq.col(job_alias.is_done).is_(True))
            )
            stmt = stmt.where(sq.or_(sq.col(Job.depends_on).is_(None), dep_is_done))

            job_is_new = sq.and_(
                Job.status == JobStatus.RUNNING,
                Job.done == 0,
            )
            stmt = stmt.where(
                sq.or_(
                    Job.status == JobStatus.PENDING,
                    job_is_new,
                )
            )

            if skip_job_ids:
                stmt = stmt.where(sq.col(Job.id).not_in(skip_job_ids))

            if skip_user_ids:
                stmt = stmt.where(
                    sq.or_(
                        Job.priority != JobPriority.LOW,
                        sq.col(Job.user_id).not_in(skip_user_ids),
                    )
                )

            if skip_domains:
                stmt = stmt.where(
                    sq.or_(
                        sq.col(Job.domain).is_(None),
                        sq.col(Job.domain).not_in(skip_domains),
                    )
                )

            if artifact is not None:
                if artifact:
                    stmt = stmt.where(Job.type == JobType.ARTIFACT)
                else:
                    stmt = stmt.where(Job.type != JobType.ARTIFACT)

            stmt = stmt.order_by(
                sq.desc(Job.priority),
                sq.asc(Job.updated_at),
            )
            return sess.exec(stmt.limit(1)).first()

    def _update(self, sess: Session, job_id: str, **values) -> None:
        sess.exec(
            sq.update(Job)
            .where(
                sq.col(Job.id) == job_id,
            )
            .values(**values)
        )

    def _update_up(
        self,
        sess: Session,
        job_id: str,
        done=Job.done,
        total=Job.total,
        failed=Job.failed,
        inclusive: bool = False,
    ) -> None:
        now = current_timestamp()

        sa_done = done
        sa_total = total
        sa_failed = failed
        sa_is_done = sa_done == sa_total
        sa_search_produced_outcome = sq.and_(
            Job.type == JobType.SEARCH_SOURCE,
            Job.extra["search_completed"].as_boolean().is_(True),
        )
        sa_all_work_failed = sq.and_(
            sa_is_done,
            sa_total > 1,
            sa_failed >= sa_total - 1,
            sq.not_(sa_search_produced_outcome),
        )

        sa_status = sq.case(
            (sa_all_work_failed, JobStatus.FAILED),
            (sq.and_(sa_is_done, sa_failed > 0), JobStatus.PARTIAL),
            (sa_is_done, JobStatus.SUCCESS),
            else_=Job.status,
        )
        sa_started_at = sq.case(
            (sq.and_(sa_is_done, sq.col(Job.started_at).is_(None)), now),
            else_=Job.started_at,
        )
        sa_finished_at = sq.case(
            (sq.and_(sa_is_done, sq.col(Job.finished_at).is_(None)), now),
            else_=Job.finished_at,
        )

        sa_pars = select_ancestors(job_id, inclusive)
        sess.exec(
            sq.update(Job)
            .where(sq.col(Job.id).in_(sa_pars))
            .where(sq.col(Job.is_done).is_(False))
            .values(
                done=sa_done,
                total=sa_total,
                failed=sa_failed,
                status=sa_status,
                is_done=sa_is_done,
                started_at=sa_started_at,
                finished_at=sa_finished_at,
            )
        )

    def _cancel_down(self, sess: Session, job_id: str, inclusive=False) -> None:
        now = current_timestamp()
        sa_deps = select_descendants(job_id, inclusive)
        sess.exec(
            sq.update(Job)
            .where(
                sq.col(Job.id).in_(sa_deps),
                sq.col(Job.is_done).is_(False),
            )
            .values(
                is_done=True,
                status=JobStatus.CANCELED,
                error="因上级任务取消而取消",
                started_at=sq.func.coalesce(Job.started_at, now),
                finished_at=sq.func.coalesce(Job.finished_at, now),
            )
        )

    def _increment_up(self, sess: Session, job_id: str, step: int = 1) -> None:
        self._update_up(
            sess,
            job_id=job_id,
            inclusive=True,
            done=Job.done + step,
        )

    def _count_pending(self, sess: Session, job_id: str) -> int:
        return sess.exec(sq.select(Job.total - Job.done).where(Job.id == job_id)).one()

    def _success(self, sess: Session, job_id: str) -> None:
        pending = self._count_pending(sess, job_id)
        self._increment_up(sess, job_id, pending)

    def _fail(
        self,
        sess: Session,
        job_id: str,
        reason: str,
        extra: Optional[dict] = None,
    ) -> None:
        pending = self._count_pending(sess, job_id)
        self._update_up(
            sess,
            job_id=job_id,
            inclusive=True,
            done=Job.done + pending,
            failed=Job.failed + pending,
        )
        self._update(
            sess,
            job_id,
            error=reason,
            status=JobStatus.FAILED,
            extra=self._get_extra(sess, job_id, extra),
        )

    def _get_extra(
        self,
        sess: Session,
        job_id: str,
        updates: Union[dict, Callable[[dict], None], None],
    ) -> dict:
        current = sess.scalar(sq.select(Job.extra).where(Job.id == job_id))

        extra = dict(current or {})
        if callable(updates):
            updates(extra)
        elif updates:
            extra.update(updates)

        return extra

    def cancel_if_dangling(self, job: Job) -> bool:
        root = self.get_root(job.id)
        # A child claimed after its root finished normally (e.g. the volume
        # batch a FULL_NOVEL creates right before completing) is a legitimate
        # in-flight job, not a dangling one — only a failed or canceled root
        # orphans its children.
        if root and not root.error:
            return False

        self.cancel(job.id)
        if root:
            if root.status == JobStatus.CANCELED:
                self.cancel(root.id)
            else:
                with ctx.db.session() as sess:
                    self._cancel_down(sess, root.id, False)
                    sess.commit()

        return True

    def update_extra(
        self,
        job: Union[Job, str],
        updates: Union[dict, Callable[[dict], None]],
    ) -> None:
        with ctx.db.session() as sess:
            job_id = job.id if isinstance(job, Job) else job
            extra = self._get_extra(sess, job_id, updates)
            sess.exec(sq.update(Job).where(sq.col(Job.id) == job_id).values(extra=extra))
            sess.commit()
            if isinstance(job, Job):
                job.extra = extra
