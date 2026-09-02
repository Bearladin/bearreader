"""Exercise the EPUB importer against a generated, harmless fixture."""

import asyncio
from io import BytesIO
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event

from ebooklib import epub
from fastapi import UploadFile
from PIL import Image
import sqlmodel

from lncrawl.context import ctx
from lncrawl.dao import Chapter, ChapterImage, ImportSession, JobStatus, Novel
from lncrawl.services.epub_import import (
    EpubImportError,
    _leading_title_cleanup,
    _parse_xml,
)
from lncrawl.services.scheduler.handlers.import_epub import (
    EpubAnalyzeHandler,
    EpubCommitHandler,
)


def _fixture_bytes(identifier: str = "fixture-id") -> bytes:
    image = BytesIO()
    Image.new("RGB", (40, 60), (20, 40, 80)).save(image, "PNG")
    book = epub.EpubBook()
    book.set_identifier(identifier)
    book.set_title("EPUB Import Fixture")
    book.add_author("Fixture Author")
    book.set_language("en")
    book.add_metadata("DC", "description", "<script>alert(1)</script>Safe synopsis")

    cover = epub.EpubImage()
    cover.file_name = "images/cover.png"
    cover.media_type = "image/png"
    cover.content = image.getvalue()
    cover.id = "cover-image"
    cover.properties = ["cover-image"]
    book.add_item(cover)

    chapters = []
    for number in range(1, 4):
        chapter = epub.EpubHtml(
            title=f"Chapter {number}",
            file_name=f"text/ch{number}.xhtml",
            lang="en",
        )
        if number == 3:
            chapter.content = (
                '<html><body><img src="../images/cover.png" onclick="bad()" /></body></html>'
            )
        else:
            chapter.content = (
                f'<html><body><h4 aria-hidden="true">#{number}</h4>'
                f"<h1>Chapter {number}</h1>"
                f"<p>Content for chapter {number}.</p>"
                '<img src="../images/cover.png" onclick="bad()" /></body></html>'
            )
        book.add_item(chapter)
        chapters.append(chapter)

    book.toc = tuple(
        epub.Link(chapter.file_name, chapter.title, f"c{number}")
        for number, chapter in enumerate(chapters, 1)
    )
    book.spine = ["nav", *chapters]
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    with TemporaryDirectory() as temporary:
        path = Path(temporary) / "fixture.epub"
        epub.write_epub(str(path), book, {})
        return path.read_bytes()


def _verify_title_cleanup_guardrails() -> None:
    from bs4 import BeautifulSoup

    exact = BeautifulSoup(
        '<body><div><h4 aria-hidden="true">#2</h4><h1>第二章 入考</h1><p>正文。</p></div></body>',
        "html.parser",
    )
    heading, marker = _leading_title_cleanup(exact.body, "第二章 入考")
    assert heading is not None and marker is not None

    rejected = [
        "<body><h1>第二章：入考</h1><p>正文。</p></body>",
        "<body><p>题记。</p><h1>第二章 入考</h1></body>",
        "<body><h4>#2</h4><h1>第二章 入考</h1></body>",
        '<body><img src="cover.jpg"/><h1>第二章 入考</h1></body>',
    ]
    for markup in rejected:
        soup = BeautifulSoup(markup, "html.parser")
        assert _leading_title_cleanup(soup.body, "第二章 入考") == (None, None)


async def _verify() -> None:
    raw = _fixture_bytes()
    user = ctx.users.get_admin()
    started = await ctx.epub_import.start_upload(
        user,
        UploadFile(file=BytesIO(raw), filename="fixture.epub"),
    )
    session_id = started["session_id"]
    analysis_job = ctx.jobs.get(started["job_id"])
    assert EpubAnalyzeHandler(analysis_job, Event()).process()

    ready = ctx.epub_import.session_view(session_id, user)
    assert ready["status"] == "ready"
    assert ready["preview"]["chapters"] == 3
    assert ready["preview"]["cover_available"] is True
    assert "&lt;script&gt;" in ready["preview"]["synopsis"]

    commit_job = ctx.epub_import.claim_commit(session_id, user, "", "")
    assert EpubCommitHandler(ctx.jobs.get(commit_job.id), Event()).process()
    completed = ctx.epub_import.session_view(session_id, user)
    assert completed["status"] == "completed"
    novel_id = completed["novel_id"]

    with ctx.db.session() as session:
        novel = session.get(Novel, novel_id)
        chapters = list(
            session.exec(sqlmodel.select(Chapter).where(Chapter.novel_id == novel_id)).all()
        )
        images = list(
            session.exec(
                sqlmodel.select(ChapterImage).where(ChapterImage.novel_id == novel_id)
            ).all()
        )
        stored_session = session.get(ImportSession, session_id)
    assert novel is not None and novel.domain == "本地导入"
    assert len(chapters) == 3 and all(chapter.is_done for chapter in chapters)
    assert len(images) == 3
    assert stored_session is not None and stored_session.novel_id == novel_id
    assert ctx.files.exists(f"novels/{novel_id}/cover.jpg")
    assert all(ctx.files.exists(chapter.content_file) for chapter in chapters)
    assert all(ctx.files.exists(image.image_file) for image in images)
    assert "onclick" not in ctx.files.load_text(chapters[0].content_file)
    assert "<h1>Chapter 1</h1>" not in ctx.files.load_text(chapters[0].content_file)
    assert "#1" not in ctx.files.load_text(chapters[0].content_file)
    assert "Content for chapter 1." in ctx.files.load_text(chapters[0].content_file)
    assert "<img" in ctx.files.load_text(chapters[2].content_file)
    assert ctx.jobs.get(commit_job.id).status == JobStatus.SUCCESS
    ctx.jobs.cancel(commit_job.id)
    assert ctx.jobs.get(commit_job.id).status == JobStatus.SUCCESS

    visible_jobs = ctx.jobs.list(user_id=user.id)
    assert all(job.type not in {analysis_job.type, commit_job.type} for job in visible_jobs.items)

    ctx.jobs.delete(analysis_job.id)
    ctx.jobs.delete(commit_job.id)
    with ctx.db.session() as session:
        assert session.get(Novel, novel_id) is not None
    assert ctx.files.exists(chapters[0].content_file)

    duplicate = await ctx.epub_import.start_upload(
        user,
        UploadFile(file=BytesIO(raw), filename="fixture.epub"),
    )
    assert duplicate["existing_novel_id"] == novel_id

    canceled_raw = _fixture_bytes("canceled-fixture-id")
    canceled_start = await ctx.epub_import.start_upload(
        user,
        UploadFile(file=BytesIO(canceled_raw), filename="canceled.epub"),
    )
    canceled_session_id = canceled_start["session_id"]
    ctx.epub_import.cancel(canceled_session_id, user)
    assert ctx.epub_import.session_view(canceled_session_id, user)["status"] == "canceled"
    ctx.epub_import.fail_session(canceled_session_id, "must not overwrite cancellation")
    assert ctx.epub_import.session_view(canceled_session_id, user)["status"] == "canceled"
    canceled_signal = Event()
    canceled_signal.set()
    canceled_job = ctx.jobs.get(canceled_start["job_id"])
    assert not EpubAnalyzeHandler(canceled_job, canceled_signal).process()
    assert ctx.jobs.get(canceled_job.id).status == JobStatus.CANCELED

    try:
        _parse_xml(b"<!DOCTYPE x [<!ENTITY a 'x'>]><container/>")
    except EpubImportError as error:
        assert "declarations" in str(error)
    else:
        raise AssertionError("unsafe XML declarations were accepted")
    print(f"Verified EPUB import: {novel_id}")


def main() -> None:
    _verify_title_cleanup_guardrails()
    previous = os.environ.get("XIAOXIONG_NOVEL_DATA_PATH")
    try:
        with TemporaryDirectory(
            prefix="bearreader-epub-verifier-", ignore_cleanup_errors=True
        ) as temporary:
            os.environ["XIAOXIONG_NOVEL_DATA_PATH"] = temporary
            ctx.setup()
            try:
                asyncio.run(_verify())
            finally:
                ctx.destroy()
    finally:
        if previous is None:
            os.environ.pop("XIAOXIONG_NOVEL_DATA_PATH", None)
        else:
            os.environ["XIAOXIONG_NOVEL_DATA_PATH"] = previous


if __name__ == "__main__":
    main()
