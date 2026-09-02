#!/usr/bin/env python3
"""
Convert PRIVACY_POLICY.md and TERMS_OF_SERVICE.md to HTML files.
Uses the markdown library for conversion.
"""

from pathlib import Path
import re

import markdown


def format_html(html: str) -> str:
    """Format HTML to match the expected style."""
    # Replace <hr> with <hr />
    html = re.sub(r"<hr\s*/?>", "<hr />", html)
    # Replace <br> with <br />
    html = re.sub(r"<br\s*/?>", "<br />", html)
    return html


def convert_file(md_path: Path, html_path: Path):
    """Convert a markdown file to HTML."""
    print(f"Converting {md_path} to {html_path}")

    md_content = md_path.read_text(encoding="utf-8")

    # Use markdown library
    md = markdown.Markdown(extensions=["extra"])
    html_content = md.convert(md_content)
    # Post-process to match format
    html_content = format_html(html_content)

    html_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.write_text(f"{html_content}\n", encoding="utf-8", newline="\n")
    print(f"✓ Generated {html_path}")


def main():
    """Main function."""
    root = Path(__file__).parent.parent
    output_dir = root / "public"

    # Convert PRIVACY_POLICY.md
    privacy_md = root / "PRIVACY_POLICY.md"
    privacy_html = output_dir / "PRIVACY_POLICY.html"

    if privacy_md.exists():
        convert_file(privacy_md, privacy_html)
    else:
        print(f"⚠ Warning: {privacy_md} not found")

    # Convert TERMS_OF_SERVICE.md
    terms_md = root / "TERMS_OF_SERVICE.md"
    terms_html = output_dir / "TERMS_OF_SERVICE.html"

    if terms_md.exists():
        convert_file(terms_md, terms_html)
    else:
        print(f"⚠ Warning: {terms_md} not found")


if __name__ == "__main__":
    main()
