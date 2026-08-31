"""Resolve and validate pages in Akbar's isolated orientation intranet."""

from __future__ import annotations

import re
from pathlib import Path

DOCUMENT_ROOT = Path(__file__).resolve().parent.parent / "aknet"
MAX_URL_LENGTH = 256
MAX_PAGE_BYTES = 16_384
URL_SEGMENT = re.compile(r"^[a-z0-9][a-z0-9-]*$")
MARKDOWN_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def resolve_aknet_url(url: str) -> Path:
    """Resolve one clean internal URL to a Markdown file under ``aknet``."""
    if not isinstance(url, str):
        raise TypeError("document URL must be a string")
    if not url or len(url) > MAX_URL_LENGTH:
        raise ValueError(
            f"document URL must contain 1 to {MAX_URL_LENGTH} characters"
        )
    if not url.startswith("/") or url.startswith("//"):
        raise ValueError("document URL must be an absolute internal path")
    if any(character in url for character in ("?", "#", "\\", "%")):
        raise ValueError("document URL cannot contain queries, fragments, or escapes")

    segments = [segment for segment in url.split("/") if segment]
    if any(not URL_SEGMENT.fullmatch(segment) for segment in segments):
        raise ValueError("document URL contains an invalid path segment")
    relative = Path(*segments) if segments else Path()
    if url == "/" or url.endswith("/"):
        relative /= "index.md"
    else:
        relative = relative.with_suffix(".md")
    resolved = (DOCUMENT_ROOT / relative).resolve(strict=False)
    if not resolved.is_relative_to(DOCUMENT_ROOT.resolve()):
        raise ValueError("document URL escapes the aknet document root")
    if not resolved.is_file():
        raise ValueError(f"aknet page not found: {url}; return to /")
    return resolved


def validate_aknet_markdown(content: str, source: Path) -> None:
    """Validate the intentionally small Markdown dialect used by aknet."""
    encoded = content.encode("utf-8")
    if len(encoded) > MAX_PAGE_BYTES:
        raise ValueError(
            f"aknet page {source.name} is {len(encoded):,} bytes; "
            f"the maximum is {MAX_PAGE_BYTES:,} bytes"
        )
    if "```" in content or "![" in content or re.search(r"<[^>]+>", content):
        raise ValueError("aknet supports text, headings, bullets, and internal links")
    for _label, target in MARKDOWN_LINK.findall(content):
        resolve_aknet_url(target)
    without_links = MARKDOWN_LINK.sub("", content)
    if "](" in without_links or "http://" in content or "https://" in content:
        raise ValueError("aknet pages may link only to valid internal URLs")
    for line in content.splitlines():
        if not line or line.startswith(("# ", "## ", "### ", "- ")):
            continue
        if line.startswith(("#", ">", "* ")) or re.match(r"^\d+\.\s", line):
            raise ValueError(
                "aknet supports plain text, three heading levels, bullets, "
                "and internal links"
            )


def load_aknet_page(url: str = "/") -> str:
    page = resolve_aknet_url(url)
    content = page.read_text(encoding="utf-8")
    validate_aknet_markdown(content, page)
    return content
