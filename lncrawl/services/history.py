from typing import Dict, Optional

from sqlalchemy.exc import IntegrityError
import sqlmodel as sq

from ..context import ctx
from ..core.taskman import TaskManager
from ..dao import Chapter, Novel, ReadHistory
from ..server.models import ContinueReadingResponse, Paginated, ReadHistoryNovel
from ..utils.time_utils import current_timestamp


class ReadHistoryService:
    def __init__(self) -> None:
        self.taskman = TaskManager(5)

    def list(
        self,
        user_id: str,
        *,
        novel_id: Optional[str] = None,
        volume_id: Optional[str] = None,
        chapter_id: Optional[str] = None,
    ) -> Dict[str, bool]:
        with ctx.db.session() as sess:
            stmt = sq.select(ReadHistory)
            stmt = stmt.where(ReadHistory.user_id == user_id)

            if novel_id:
                ids = [x.strip() for x in novel_id.split(",")]
                stmt = stmt.where(
                    sq.col(ReadHistory.novel_id).in_(ids),
                )
            if volume_id:
                ids = [x.strip() for x in volume_id.split(",")]
                stmt = stmt.where(
                    sq.col(ReadHistory.volume_id).in_(ids),
                )
            if chapter_id:
                ids = [x.strip() for x in chapter_id.split(",")]
                stmt = stmt.where(
                    sq.col(ReadHistory.chapter_id).in_(ids),
                )

            items = sess.exec(stmt).all()
            return {item.chapter_id: True for item in items}

    def list_recent_novels(
        self, user_id: str, offset: int, limit: int
    ) -> Paginated[ReadHistoryNovel]:
        """List the novels a user has read, most-recently-read first.

        Each entry carries the last-read chapter (a resume target for the
        reader) and how many chapters of the novel have been read.
        """
        with ctx.db.session() as sess:
            total = (
                sess.exec(
                    sq.select(
                        sq.func.count(
                            sq.distinct(sq.col(ReadHistory.novel_id)),
                        ),
                    ).where(
                        ReadHistory.user_id == user_id,
                    )
                ).one()
                or 0
            )

            rows = sess.exec(
                sq.select(
                    ReadHistory.novel_id,
                    sq.func.max(ReadHistory.created_at),
                    sq.func.count(),
                )
                .where(ReadHistory.user_id == user_id)
                .group_by(sq.col(ReadHistory.novel_id))
                .order_by(sq.func.max(ReadHistory.created_at).desc())
                .offset(offset)
                .limit(limit)
            ).all()

            novel_ids = [r[0] for r in rows]
            if not novel_ids:
                return Paginated(total=total, offset=offset, limit=limit, items=[])

            novels = {
                n.id: n
                for n in sess.exec(
                    sq.select(Novel).where(
                        sq.col(Novel.id).in_(novel_ids),
                    )
                ).all()
            }

            # Resolve the most-recently-read chapter per novel (resume target).
            # Bounded to the page's novels; read_history is tier-capped per user.
            last_chapter: Dict[str, str] = {}
            chapter_rows = sess.exec(
                sq.select(ReadHistory.novel_id, ReadHistory.chapter_id)
                .where(ReadHistory.user_id == user_id)
                .where(sq.col(ReadHistory.novel_id).in_(novel_ids))
                .order_by(sq.desc(ReadHistory.created_at))
            ).all()
            for novel_id, chapter_id in chapter_rows:
                last_chapter.setdefault(novel_id, chapter_id)

            items = [
                ReadHistoryNovel(
                    novel=novels[novel_id],
                    last_read_at=int(last_read),
                    last_chapter_id=last_chapter.get(novel_id),
                    read_count=int(read_count),
                )
                for novel_id, last_read, read_count in rows
                if novel_id in novels
            ]

        return Paginated(total=total, offset=offset, limit=limit, items=items)

    def continue_reading(self, user_id: str, novel_id: str) -> ContinueReadingResponse:
        """Resolve where the user should (re)start reading a novel.

        Returns the most recently opened chapter when any history exists;
        otherwise falls back to the first chapter.
        """
        with ctx.db.session() as sess:
            chapter_id = sess.exec(
                sq.select(ReadHistory.chapter_id)
                .where(ReadHistory.user_id == user_id)
                .where(ReadHistory.novel_id == novel_id)
                .order_by(sq.col(ReadHistory.created_at).desc())
                .limit(1)
            ).first()

            if not chapter_id:
                # nothing read yet; fall back to the first chapter
                chapter_id = sess.exec(
                    sq.select(Chapter.id)
                    .where(Chapter.novel_id == novel_id)
                    .order_by(sq.col(Chapter.serial).asc())
                    .limit(1)
                ).first()
                return ContinueReadingResponse(
                    chapter_id=chapter_id,
                    has_history=False,
                )

            return ContinueReadingResponse(
                chapter_id=chapter_id,
                has_history=True,
            )

    def check(self, user_id: str, chapter_id: str) -> bool:
        with ctx.db.session() as sess:
            item = sess.exec(
                sq.select(ReadHistory.id)
                .where(ReadHistory.user_id == user_id)
                .where(ReadHistory.chapter_id == chapter_id)
            ).first()
            return bool(item)

    def add(self, user_id: str, chapter_id: str) -> None:
        with ctx.db.session() as sess:
            chapter = ctx.chapters.get(chapter_id)
            # Re-opening the same chapter refreshes its created_at so it
            # becomes the "most recently opened" resume target (no new field).
            existing = sess.exec(
                sq.select(ReadHistory)
                .where(ReadHistory.user_id == user_id)
                .where(ReadHistory.chapter_id == chapter_id)
                .limit(1)
            ).first()
            if existing:
                existing.created_at = current_timestamp()
                sess.add(existing)
                sess.commit()
                return

            try:
                history = ReadHistory(
                    user_id=user_id,
                    chapter_id=chapter_id,
                    novel_id=chapter.novel_id,
                    volume_id=chapter.volume_id,
                )
                sess.add(history)
                sess.commit()
                self.taskman.submit_task(self.prune, user_id)
            except IntegrityError:
                sess.rollback()
                return

    def prune(self, user_id: str) -> None:
        user = ctx.users.get(user_id)
        limit = ctx.tier.max_read_history(user)
        if limit is None:
            return
        with ctx.db.session() as sess:
            tbd = (
                sq.select(ReadHistory.id)
                .where(ReadHistory.user_id == user_id)
                .order_by(sq.desc(ReadHistory.created_at))
                .offset(limit)
                .scalar_subquery()
            )
            stmt = sq.delete(ReadHistory).where(
                sq.col(ReadHistory.id).in_(tbd),
            )
            sess.exec(stmt)
            sess.commit()
