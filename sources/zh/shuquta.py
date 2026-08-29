# -*- coding: utf-8 -*-
import logging

from lncrawl.core import Novel, PageSoup, SoupTemplate

logger = logging.getLogger(__name__)


class ShuQuTaCrawler(SoupTemplate):
    base_url = ["http://www.shuquta.com/"]
    language = "zh-cn"
    # 站内搜索不可用（search.php 无结果、/search.html 404），仅支持粘贴 URL 抓取。

    novel_title_selector = 'meta[property="og:novel:book_name"]'
    novel_cover_selector = 'meta[property="og:image"]'
    novel_author_selector = 'meta[property="og:novel:author"]'
    novel_synopsis_selector = 'meta[property="og:description"]'

    chapter_list_selector = "div.book_list li"
    chapter_title_selector = "a"
    chapter_url_selector = "a"
    chapter_body_selector = "div#content"

    def initialize(self) -> None:
        self.cleaner.bad_css.update({"script", "style"})
        # 正文开头有一段站点面包屑（说说520 > 分类 > 书名 > 章节）。
        self.cleaner.bad_tag_text_pairs["b"] = "说说520"
        # 正文里的章节导航行（加入书签 / 上一页 / 目录 / 下一页）。
        self.cleaner.bad_tag_text_pairs["p"] = "加入书签"

    def parse_title(self, soup: PageSoup, novel: Novel) -> None:
        # The OpenGraph tags live after <title>, so the base-class fallback
        # would pick the <title> tag (which has no `content`); read the meta.
        tag = soup.select_one(self.novel_title_selector)
        novel.title = (tag.get("content") or "").strip() if tag else ""

    def parse_authors(self, soup: PageSoup, novel: Novel) -> None:
        tag = soup.select_one(self.novel_author_selector)
        novel.author = (tag.get("content") or "").strip() if tag else ""
