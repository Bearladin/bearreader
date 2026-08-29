import re
from typing import Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from bs4.element import NavigableString

# --- Tag -> single-URL attributes ------------------------------------------------
_URL_ATTRS = {
    "a": ("href",),
    "applet": ("codebase", "archive"),
    "area": ("href",),
    "audio": ("src",),
    "base": ("href",),
    "blockquote": ("cite",),
    "body": ("background",),
    "button": ("formaction",),
    "del": ("cite",),
    "embed": ("src",),
    "form": ("action",),
    "frame": ("src", "longdesc"),
    "iframe": ("src", "longdesc"),
    "image": ("href", "xlink:href"),  # inline SVG <image>
    "img": ("src", "longdesc", "lowsrc"),
    "input": ("src", "formaction"),
    "ins": ("cite",),
    "link": ("href",),
    "object": ("data", "codebase", "classid"),
    "q": ("cite",),
    "script": ("src",),
    "source": ("src",),
    "track": ("src",),
    "use": ("href", "xlink:href"),  # inline SVG <use>
    "video": ("src", "poster"),
}

# Checked on every tag regardless of name (SVG foreign-content attribute).
_GLOBAL_URL_ATTRS = ("xlink:href",)

# Attributes holding a comma-separated "url descriptor" list.
_SRCSET_ATTRS = ("srcset", "imagesrcset")

# Attributes that may contain a space-separated list of URLs.
_LIST_ATTRS = {"a": ("ping",)}

# Common lazy-loading attributes used by JS-driven sites. Only rewritten if
# the value actually looks like a URL/path (heuristic, see _looks_like_url).
_LAZY_ATTRS = (
    "data-src",
    "data-original",
    "data-lazy",
    "data-lazy-src",
    "data-actualsrc",
    "data-thumb",
    "data-href",
    "data-url",
    "data-bg",
    "data-background",
    "data-original-src",
    "data-srcset",
    "data-cfsrc",
    "data-ezsrc",
)

# OpenGraph / Twitter-card <meta content="..."> values that are URLs.
_META_URL_PROPERTIES = {
    "og:url",
    "og:image",
    "og:image:url",
    "og:image:secure_url",
    "og:video",
    "og:video:url",
    "og:video:secure_url",
    "og:audio",
    "twitter:image",
    "twitter:image:src",
    "twitter:player",
    "twitter:player:stream",
}

# Schemes that are never relative and must be left untouched.
_SKIP_SCHEMES = {
    "javascript",
    "data",
    "mailto",
    "tel",
    "sms",
    "callto",
    "whatsapp",
    "about",
    "blob",
    "file",
    "magnet",
    "intent",
    "geo",
    "market",
    "ws",
    "wss",
    "void",
    "skype",
}

_SCHEME_RE = re.compile(r"^([a-zA-Z][a-zA-Z0-9+.\-]*):")
_WS_RE = re.compile(r"[\t\r\n]+")

# CSS url(...) and @import "..." / @import url(...)
_CSS_URL_RE = re.compile(r"url\(\s*(['\"]?)(.*?)\1\s*\)", re.IGNORECASE)
_CSS_IMPORT_RE = re.compile(r"@import\s+(?:url\(\s*)?(['\"]?)([^'\")\s]+)\1\)?", re.IGNORECASE)

# <meta http-equiv="refresh" content="5; url=...">
_META_REFRESH_RE = re.compile(r"(url\s*=\s*)(['\"]?)([^'\";]+)\2?", re.IGNORECASE)

# srcset attribute
_SRCSET_SPLIT_RE = re.compile(r"\s*,\s*")
_SRCSET_ITEM_RE = re.compile(r"^(\S+)(\s+.+)?$")


def _clean_url(value: str) -> Optional[str]:
    """Strip wrapping/embedded whitespace and bail out on non-relative schemes."""
    if not isinstance(value, str):
        return None
    cleaned = _WS_RE.sub("", value).strip()
    if not cleaned:
        return ""  # empty -> resolves to the document/base URL itself
    m = _SCHEME_RE.match(cleaned)
    if m and m.group(1).lower() in _SKIP_SCHEMES:
        return None
    return cleaned


def _looks_like_url(value: str) -> bool:
    value = value.strip()
    if not value:
        return False
    # Reject obvious non-URL payloads sometimes stuffed into data-* attrs.
    if value[0] in "{[" or value.lower() in ("true", "false", "null"):
        return False
    return True


def _abs(value: str, base: str) -> Optional[str]:
    cleaned = _clean_url(value)
    if cleaned is None:
        return None
    try:
        return urljoin(base, cleaned)
    except ValueError:
        return None


def rewrite_srcset(value: str, base: str) -> str:
    out = []
    for item in _SRCSET_SPLIT_RE.split(value.strip()):
        item = item.strip()
        if not item:
            continue
        m = _SRCSET_ITEM_RE.match(item)
        if not m:
            out.append(item)
            continue
        url, descriptor = m.group(1), m.group(2) or ""
        new_url = _abs(url, base)
        out.append((new_url if new_url is not None else url) + descriptor)
    return ", ".join(out)


def rewrite_css(css: str, base: str) -> str:
    def _import_sub(m):
        _, url = m.group(1), m.group(2)
        new_url = _abs(url, base)
        return f'@import "{new_url if new_url is not None else url}"'

    def _url_sub(m):
        quote, url = m.group(1), m.group(2)
        new_url = _abs(url, base)
        new_url = new_url if new_url is not None else url
        return f"url({quote}{new_url}{quote})"

    css = _CSS_IMPORT_RE.sub(_import_sub, css)
    css = _CSS_URL_RE.sub(_url_sub, css)
    return css


def rewrite_meta_refresh(content: str, base: str) -> str:
    def _sub(m):
        prefix, quote, url = m.group(1), m.group(2), m.group(3)
        new_url = _abs(url, base)
        new_url = new_url if new_url is not None else url
        return f"{prefix}{quote}{new_url}{quote}"

    return _META_REFRESH_RE.sub(_sub, content, count=1)


def replace_links(content: str, base_url: str) -> str:
    content = content.replace("http://", f"{base_url}/http://")
    content = content.replace("https://", f"{base_url}/https://")
    return content


def rewrite_html(html: str, base_url: str) -> str:
    soup = BeautifulSoup(html, "lxml")

    # Respect an in-page <base href>: it changes the resolution base for
    # every other relative URL in the document.
    effective_base = base_url
    base_tag = soup.find("base", href=True)
    if base_tag:
        href = str(base_tag["href"])
        resolved = _abs(href, base_url)
        if resolved:
            effective_base = resolved

    for tag in soup.find_all(True):
        name = tag.name

        # 1. Tag-specific single-URL attributes (href, src, action, cite, ...)
        for attr in _URL_ATTRS.get(name, ()) + _GLOBAL_URL_ATTRS:
            value = tag.get(attr)
            if isinstance(value, str):
                new_value = _abs(value, effective_base)
                if new_value is not None:
                    tag[attr] = new_value

        # 2. Space-separated URL lists (e.g. <a ping="...">)
        for attr in _LIST_ATTRS.get(name, ()):
            value = tag.get(attr)
            if isinstance(value, str) and value.strip():
                parts = []
                for part in value.split():
                    new_part = _abs(part, effective_base)
                    parts.append(new_part if new_part is not None else part)
                tag[attr] = " ".join(parts)

        # 3. srcset / imagesrcset
        for attr in _SRCSET_ATTRS:
            value = tag.get(attr)
            if isinstance(value, str) and value.strip():
                tag[attr] = rewrite_srcset(value, effective_base)

        # 4. Lazy-loading data-* attributes (best-effort, heuristic)
        for attr in _LAZY_ATTRS:
            value = tag.get(attr)
            if not isinstance(value, str) or not value.strip():
                continue
            if attr.endswith("srcset"):
                tag[attr] = rewrite_srcset(value, effective_base)
            elif _looks_like_url(value):
                new_value = _abs(value, effective_base)
                if new_value is not None:
                    tag[attr] = new_value

        # 5. Inline style="...url(...)..."
        style = tag.get("style")
        if isinstance(style, str) and "url(" in style.lower():
            tag["style"] = rewrite_css(style, effective_base)

        # 6. <style>...</style> blocks (url() and @import)
        if name == "style" and isinstance(tag.string, NavigableString):
            tag.string.replace_with(rewrite_css(str(tag.string), effective_base))

        # 7. <meta http-equiv="refresh" content="5;url=...">
        #    and OpenGraph / Twitter card image/url meta tags
        if name == "meta":
            content = tag.get("content")
            if isinstance(content, str):
                http_equiv = str(tag.get("http-equiv") or "").lower()
                if http_equiv == "refresh":
                    tag["content"] = rewrite_meta_refresh(content, effective_base)

                prop = str(tag.get("property") or tag.get("name") or "").lower()
                if prop in _META_URL_PROPERTIES:
                    new_value = _abs(content, effective_base)
                    if new_value is not None:
                        tag["content"] = new_value

    return str(soup)
