from __future__ import annotations

import sys
from urllib.parse import urlsplit
import webbrowser

from ..exceptions import ServerErrors

_MAX_EXTERNAL_URL_LENGTH = 4096


def validate_external_url(url: str) -> str:
    if len(url) > _MAX_EXTERNAL_URL_LENGTH or any(ord(char) < 32 for char in url):
        raise ServerErrors.invalid_input.with_extra("外部链接过长")
    parsed = urlsplit(url)
    if (
        parsed.scheme.lower() not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise ServerErrors.invalid_input.with_extra("只允许打开安全的 HTTP 或 HTTPS 链接")
    return url


class DesktopService:
    def open_external(self, url: str) -> None:
        """Open one validated web URL through the operating-system browser."""
        url = validate_external_url(url)

        if sys.platform == "win32":
            import os

            os.startfile(url)  # type: ignore[attr-defined]
            return
        if not webbrowser.open(url, new=2):
            raise ServerErrors.invalid_input.with_extra("系统浏览器无法打开这个链接")
