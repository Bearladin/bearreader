# -*- coding: utf-8 -*-
import logging
import re
from typing import Iterable, Optional

from lncrawl.core import Novel, PageSoup, SoupTemplate, Volume

logger = logging.getLogger(__name__)

# The reading page lives at /mm/<id>/ and carries the full chapter list plus the
# OpenGraph metadata; the sibling /mminfo/<id>/ page is a description page without
# the list. Search is front-end signed (/api/search with token params), so it is
# not exposed as a crawler feature.
BOOK_ID = re.compile(r"/(?:mm|mminfo)/(\d+)/?$")
AD_TITLE = re.compile(r"^推荐")


class NiebaCrawler(SoupTemplate):
    base_url = ["https://www.nieba.net/"]
    language = "zh-cn"

    novel_title_selector = 'meta[property="og:title"]'
    novel_author_selector = 'meta[property="og:novel:author"]'
    novel_synopsis_selector = 'meta[property="og:description"]'
    chapter_body_selector = "div#htmlContent"

    chapter_title_selector = "a"
    chapter_url_selector = "a"

    def initialize(self) -> None:
        self.cleaner.bad_css.update({"script"})

    def parse_title(self, soup: PageSoup, novel: Novel) -> None:
        # The OpenGraph tags live after <title>, so the base-class fallback would
        # pick the <title> tag (which has no `content`); read the meta directly.
        tag = soup.select_one(self.novel_title_selector)
        novel.title = (tag.get("content") or "").strip() if tag else ""

    def parse_authors(self, soup: PageSoup, novel: Novel) -> None:
        tag = soup.select_one(self.novel_author_selector)
        novel.author = (tag.get("content") or "").strip() if tag else ""

    def parse_summary(self, soup: PageSoup, novel: Novel) -> None:
        tag = soup.select_one(self.novel_synopsis_selector)
        novel.synopsis = (tag.get("content") or "").strip() if tag else ""

    def build_novel_url(self, novel: Novel) -> str:
        # Normalise the /mminfo/<id>/ description page to the /mm/<id>/ reading
        # page, which carries the chapter list and the OpenGraph metadata.
        url = self.absolute_url(novel.url)
        return re.sub(r"/mminfo/(\d+)/?$", r"/mm/\1/", url)

    def parse_cover(self, soup: PageSoup, novel: Novel) -> None:
        # The reading page has no <img>; the cover sits at the standard path
        # /img/<first-two-digits>/<id>.jpg.
        match = BOOK_ID.search(self.absolute_url(novel.url))
        if match:
            book_id = match.group(1)
            novel.cover_url = f"{self.scraper.origin}/img/{book_id[:2]}/{book_id}.jpg"

    def select_chapter_tags(
        self, tag: PageSoup, novel: Novel, volume: Optional[Volume] = None
    ) -> Iterable[PageSoup]:
        rows = []
        for a in tag.select("table#at td a[href]"):
            title = (a.get("title") or a.text or "").strip()
            # The list ends with a "推荐新文" promotion row, not a chapter.
            if AD_TITLE.match(title):
                continue
            rows.append(a)
        return rows
