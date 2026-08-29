# -*- coding: utf-8 -*-
import logging
import re
from typing import Iterable, Optional
from urllib.parse import urlencode

from lncrawl.core import Novel, PageSoup, SoupTemplate, Volume

logger = logging.getLogger(__name__)

AUTHOR_LABEL = re.compile(r"^作\s*者[:：]\s*", re.U)

# A chapter that spans several pages is served as /<bucket>_<book>/<chapter>/<n>.html;
# the "下一页" link leaves that path once the chapter is complete.
SEARCH_URL = "https://www.mayiwsk.com/modules/article/search.php"


class MayiWskCrawler(SoupTemplate):
    base_url = ["https://www.mayiwsk.com/"]
    language = "zh-cn"
    can_search = True

    novel_title_selector = "div#maininfo h1"
    novel_cover_selector = "img[src*='article/image']"
    novel_synopsis_selector = "div#intro"
    chapter_body_selector = "div#content"

    search_item_list_selector = "table.grid tr[id='nr']"
    search_item_title_selector = "td:first-child a"
    search_item_url_selector = "td:first-child a"
    search_item_info_selector = "td:nth-child(3)"

    chapter_title_selector = "a"
    chapter_url_selector = "a"

    def initialize(self) -> None:
        self.cleaner.bad_css.update({"script", "div#center_tip"})

    def select_search_item_list(self, query: str) -> Iterable[PageSoup]:
        data = urlencode({"searchtype": "articlename", "searchkey": query})
        response = self.scraper.submit_form(SEARCH_URL, data=data)
        soup = self.scraper.make_soup(response)
        return soup.select(self.search_item_list_selector)

    def parse_authors(self, soup: PageSoup, novel: Novel) -> None:
        meta = soup.select_one("div#info p")
        text = (meta.text or "") if meta else ""
        novel.author = AUTHOR_LABEL.sub("", text).strip()

    def select_chapter_tags(
        self, tag: PageSoup, novel: Novel, volume: Optional[Volume] = None
    ) -> Iterable[PageSoup]:
        # The single <dl> lists "最新章节" (newest first) then "正文" (reading order),
        # split by <dt> headings; only the body section after the 正文 <dt> is wanted.
        dl = tag.select_one("dl")
        if dl is None:
            return []
        body_dt = next((dt for dt in dl.select("dt") if "正文" in (dt.text or "")), None)
        if body_dt is None:
            return list(dl.select("dd a[href]"))
        return list(body_dt.find_next_siblings("dd"))
