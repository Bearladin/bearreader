# -*- coding: utf-8 -*-
import logging
import re
from typing import Iterable, List, Optional

from lncrawl.core import Chapter, Novel, PageSoup, SoupTemplate, Volume
from lncrawl.exceptions import LNException

logger = logging.getLogger(__name__)

BOOK_ID = re.compile(r"/du_(\d+)/")
# The full catalog is rendered by JavaScript; the detail page only shows a
# "latest chapters" strip, so chapter URLs are generated from the total count
# ("共 N 章节") and their titles are filled in while downloading.
TOTAL_CHAPTERS = re.compile(r"共\s*(\d+)\s*章节")
PAGE_SUFFIX = re.compile(r"\(\d+\)$")


class DuShuLaiCrawler(SoupTemplate):
    base_url = ["https://www.dushulai.com/"]
    language = "zh-cn"
    # 站内搜索返回空结果页，仅支持粘贴 URL 抓取。

    novel_title_selector = 'meta[property="og:novel:book_name"]'
    novel_cover_selector = 'meta[property="og:image"]'
    novel_author_selector = 'meta[property="og:novel:author"]'
    novel_synopsis_selector = 'meta[property="og:description"]'

    chapter_title_selector = "a"
    chapter_url_selector = "a"
    chapter_body_selector = "div#chaptercontent"

    def initialize(self) -> None:
        self.cleaner.bad_css.update({"script", "style"})

    def parse_title(self, soup: PageSoup, novel: Novel) -> None:
        # The OpenGraph tags live after <title>, so the base-class fallback
        # would pick the <title> tag (which has no `content`); read the meta.
        tag = soup.select_one(self.novel_title_selector)
        novel.title = (tag.get("content") or "").strip() if tag else ""

    def parse_authors(self, soup: PageSoup, novel: Novel) -> None:
        tag = soup.select_one(self.novel_author_selector)
        novel.author = (tag.get("content") or "").strip() if tag else ""

    def select_chapter_tags(
        self, tag: PageSoup, novel: Novel, volume: Optional[Volume] = None
    ) -> Iterable[PageSoup]:
        match = BOOK_ID.search(novel.url)
        if not match:
            return []
        bid = match.group(1)
        total = TOTAL_CHAPTERS.search(str(tag))
        if not total:
            raise LNException(f"Failed to parse total chapter count for {novel.url}")
        count = int(total.group(1))
        tags: List[PageSoup] = []
        for index in range(count):
            # 0.html 是第 1 章，N-1.html 是第 N 章；标题在下载章节时从页面补齐。
            tags.append(
                self.scraper.make_soup(f'<a href="/du_{bid}/{index}.html">第{index + 1}章</a>')
            )
        return tags

    def download_chapter(self, chapter: Chapter) -> None:
        url = self.build_chapter_url(chapter)
        soup = self.scraper.get_soup(url)
        body = soup.select_one(self.chapter_body_selector)
        self.parse_chapter_body(body, chapter)
        # 目录由 URL 生成，标题始终以章节页为准。
        h1 = soup.select_one("h1")
        if h1:
            chapter.title = PAGE_SUFFIX.sub("", h1.text.strip())
