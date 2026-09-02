"""Verify that BearReader's source and embedded shells disable browser translation."""

from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent


def verify_shell(path: Path) -> None:
    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
    root = soup.find("html")
    assert root is not None
    assert root.get("lang") == "zh-CN"
    assert root.get("translate") == "no"
    marker = soup.find("meta", attrs={"name": "google"})
    assert marker is not None
    assert str(marker.get("content") or "").lower() == "notranslate"


def main() -> None:
    verify_shell(ROOT / "frontend" / "index.html")
    verify_shell(ROOT / "lncrawl" / "server" / "web" / "index.html")
    print("Verified non-translatable BearReader shells")


if __name__ == "__main__":
    main()
