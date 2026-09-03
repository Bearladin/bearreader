# -*- coding: utf-8 -*-
from __future__ import annotations

import re
from typing import Iterable, List
import unicodedata
from urllib.parse import urlsplit, urlunsplit

from lncrawl.core import Chapter, Novel, PageSoup, SearchResult, SoupTemplate, Volume
from lncrawl.exceptions import LNException

_BOOK_PATH = re.compile(r"^/book/(?P<book_id>\d+)/?$")
_CHAPTER_PATH = re.compile(r"^/book/(?P<book_id>\d+)/\d+\.html$")
_CHAPTER_HEADING = re.compile(r"^第\s*\d+\s*章\s*(?P<title>.+?)\s*$")
_CHAPTER_END = re.compile(r"^[（(]\s*本章完\s*[）)]$")


def _heading_title(value: str) -> str:
    match = _CHAPTER_HEADING.fullmatch(value.strip())
    if not match:
        return ""
    title = unicodedata.normalize("NFKC", match.group("title"))
    return re.sub(r"\s+", "", title).strip("：:、.．-—_")


def _book_url(value: str) -> str:
    parsed = urlsplit(value)
    path = f"{parsed.path.rstrip('/')}/"
    return urlunsplit((parsed.scheme, parsed.netloc, path, "", ""))


class UukanshuCcCrawler(SoupTemplate):
    base_url = ["https://uukanshu.cc/"]
    language = "zh-tw"
    can_search = True
    request_rate_limit = 1.0

    novel_title_selector = "h1.booktitle"
    novel_cover_selector = 'meta[property="og:image"]'
    novel_author_selector = 'meta[property="og:novel:author"]'
    novel_tags_selector = 'meta[property="og:novel:category"]'
    novel_synopsis_selector = 'meta[property="og:description"]'

    chapter_list_selector = "#list-chapterAll a[href]"
    chapter_body_selector = ".readcotent"

    def search(self, query: str) -> Iterable[SearchResult]:
        response = self.scraper.post(
            self.absolute_url("/search"),
            data={"searchkey": query, "searchtype": "all"},
        )
        final_url = str(response.url)
        soup = self.scraper.make_soup(response)
        final = urlsplit(final_url)

        if final.hostname == "uukanshu.cc" and _BOOK_PATH.fullmatch(final.path):
            title = soup.select_one(self.novel_title_selector).text.strip()
            if not title:
                raise LNException(f"Failed to parse exact search result: {final_url}")
            author = soup.select_one(self.novel_author_selector).get("content").strip()
            info = f"作者：{author}" if author else ""
            return [
                SearchResult(title=title, url=_book_url(self.absolute_url(final_url)), info=info)
            ]

        results: List[SearchResult] = []
        seen: set[str] = set()
        for item in soup.select(".bookbox"):
            anchor = item.select_one(".bookinfo .bookname a[href]")
            title = anchor.text.strip()
            url = self.absolute_url(anchor.get("href"), page_url=final_url)
            parsed = urlsplit(url)
            if (
                not title
                or parsed.hostname != "uukanshu.cc"
                or not _BOOK_PATH.fullmatch(parsed.path)
            ):
                continue
            canonical = _book_url(url)
            if canonical in seen:
                continue
            seen.add(canonical)
            info = item.select_one(".bookinfo .author").text.strip()
            results.append(SearchResult(title=title, url=canonical, info=info))
        return results

    def build_novel_url(self, novel: Novel) -> str:
        return _book_url(self.absolute_url(novel.url))

    def parse_authors(self, soup: PageSoup, novel: Novel) -> None:
        novel.author = soup.select_one(self.novel_author_selector).get("content").strip()

    def parse_tags(self, soup: PageSoup, novel: Novel) -> None:
        category = soup.select_one(self.novel_tags_selector).get("content").strip()
        novel.tags = [category] if category else []

    def select_chapter_tags(
        self,
        tag: PageSoup,
        novel: Novel,
        volume: Volume | None = None,
    ) -> Iterable[PageSoup]:
        novel_url = urlsplit(self.absolute_url(novel.url))
        book_match = _BOOK_PATH.fullmatch(novel_url.path)
        if novel_url.hostname != "uukanshu.cc" or not book_match:
            raise LNException(f"Invalid uukanshu.cc novel URL: {novel.url}")
        book_id = book_match.group("book_id")

        chapters: List[PageSoup] = []
        seen: set[str] = set()
        for anchor in tag.select(self.chapter_list_selector):
            url = self.absolute_url(anchor.get("href"), page_url=novel.url)
            parsed = urlsplit(url)
            chapter_match = _CHAPTER_PATH.fullmatch(parsed.path)
            if (
                parsed.hostname != "uukanshu.cc"
                or not chapter_match
                or chapter_match.group("book_id") != book_id
            ):
                continue
            canonical = urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))
            if canonical in seen:
                continue
            seen.add(canonical)
            if anchor.tag is not None:
                anchor.tag["href"] = canonical
            chapters.append(anchor)
        return chapters

    def parse_chapter_body(self, soup: PageSoup, chapter: Chapter) -> None:
        html = self.cleaner.extract_contents(soup)
        body = PageSoup.create(f"<div>{html}</div>").select_one("div")
        paragraphs = body.select("p")

        if paragraphs:
            first = paragraphs[0].text.strip()
            expected = _heading_title(chapter.title)
            first_tag = paragraphs[0].tag
            if (
                first_tag is not None
                and len(first) <= 80
                and expected
                and _heading_title(first) == expected
            ):
                first_tag.decompose()

        paragraphs = body.select("p")
        if paragraphs and _CHAPTER_END.fullmatch(paragraphs[-1].text.strip()):
            last_tag = paragraphs[-1].tag
            if last_tag is not None:
                last_tag.decompose()

        chapter.body = body.inner_html
