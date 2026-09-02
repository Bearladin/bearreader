"""Exercise bounded TXT analysis/formatting and the shared import lifecycle."""

import asyncio
from io import BytesIO
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event

from fastapi import UploadFile
import sqlmodel

from lncrawl.context import ctx
from lncrawl.dao import Chapter, Novel
from lncrawl.services.imports.txt import TxtAdapter, format_txt_body
from lncrawl.services.scheduler.handlers.import_epub import (
    EpubAnalyzeHandler,
    EpubCommitHandler,
)


def _verify_adapter(root: Path) -> None:
    text = (
        "第一章 开始\r\n\r\n"
        "第一段硬换行\r\n继续。\r\n\r\n"
        "第二章 继续\r\n<script>alert(1)</script>正文。\r\n"
    )
    for encoding in ("utf-8-sig", "utf-16", "gb18030"):
        source = root / f"fixture-{encoding}.txt"
        source.write_bytes(text.encode(encoding))
        prepared = root / f"prepared-{encoding}"
        requested = "gb18030" if encoding == "gb18030" else None
        preview, manifest = TxtAdapter().analyze(
            source,
            prepared,
            Event(),
            lambda _phase: None,
            {"encoding": requested} if requested else {},
        )
        assert preview["source_format"] == "txt"
        assert preview["chapters"] == 2
        assert len(preview["samples"]) <= 3
        assert "normalized_text" not in manifest
        chapters = list(TxtAdapter().iter_chapters(prepared, manifest, Event()))
        assert len(chapters) == 2
        assert "<script>" not in chapters[1]["body"]
        assert "&lt;script&gt;" in chapters[1]["body"]

    sample = "一行\n二行\n\n三行"
    assert "<p>" in format_txt_body(sample, "block")
    assert format_txt_body(sample, "single").count("<p>") == 3
    assert "<br" in format_txt_body(sample, "unformatted")
    assert format_txt_body("hello\nworld", "block") == "<p>hello world</p>"
    assert format_txt_body("中文\n换行", "block") == "<p>中文换行</p>"


async def _verify_lifecycle() -> None:
    user = ctx.users.get_admin()
    raw = "第一章 开始\n\n第一段。\n\n第二章 继续\n\n第二段。\n".encode()
    started = await ctx.book_import.start_txt_upload(
        user,
        UploadFile(file=BytesIO(raw), filename="TXT 导入测试.txt"),
    )
    session_id = str(started["session_id"])
    analysis = ctx.jobs.get(str(started["job_id"]))
    assert EpubAnalyzeHandler(analysis, Event()).process()
    ready = ctx.book_import.session_view(session_id, user)
    assert ready["source_format"] == "txt"
    assert ready["status"] == "ready"
    assert ready["preview"]["chapters"] == 2

    reanalysis = ctx.book_import.reanalyze_txt(
        session_id,
        user,
        {"encoding": "utf-8", "paragraph_mode": "single", "unwrap_lines": True},
    )
    assert EpubAnalyzeHandler(ctx.jobs.get(reanalysis.id), Event()).process()
    ready = ctx.book_import.session_view(session_id, user)
    assert ready["status"] == "ready"
    assert ready["preview"]["resolved_paragraph_mode"] == "single"

    commit = ctx.book_import.claim_commit(session_id, user, "", "")
    assert EpubCommitHandler(ctx.jobs.get(commit.id), Event()).process()
    completed = ctx.book_import.session_view(session_id, user)
    novel_id = str(completed["novel_id"])
    with ctx.db.session() as session:
        novel = session.get(Novel, novel_id)
        chapters = list(
            session.exec(sqlmodel.select(Chapter).where(Chapter.novel_id == novel_id)).all()
        )
    assert novel is not None and novel.extra["source_format"] == "txt"
    assert len(chapters) == 2
    assert all(chapter.extra["source_format"] == "txt" for chapter in chapters)
    assert all(ctx.files.exists(chapter.content_file) for chapter in chapters)
    print(f"Verified TXT import: {novel_id}")


def main() -> None:
    previous = os.environ.get("XIAOXIONG_NOVEL_DATA_PATH")
    try:
        with TemporaryDirectory(prefix="bearreader-book-verifier-") as temporary:
            root = Path(temporary)
            _verify_adapter(root)
            os.environ["XIAOXIONG_NOVEL_DATA_PATH"] = str(root / "data")
            ctx.setup()
            try:
                asyncio.run(_verify_lifecycle())
            finally:
                ctx.destroy()
    finally:
        if previous is None:
            os.environ.pop("XIAOXIONG_NOVEL_DATA_PATH", None)
        else:
            os.environ["XIAOXIONG_NOVEL_DATA_PATH"] = previous


if __name__ == "__main__":
    main()
