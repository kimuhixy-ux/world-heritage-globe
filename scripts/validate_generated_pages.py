#!/usr/bin/env python3
"""Validate generated heritage pages and ensure source descriptions are absent."""

from __future__ import annotations

import json
import html
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = 1258


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def main() -> None:
    data = json.loads((ROOT / "data/heritage.json").read_text(encoding="utf-8"))
    descriptions = {value for item in data for value in (item.get("description"), item.get("descriptionJa")) if value}
    ja = sorted((ROOT / "items").glob("*/index.html"))
    en = sorted((ROOT / "en/items").glob("*/index.html"))
    if len(ja) != EXPECTED or len(en) != EXPECTED:
        fail(f"page count ja={len(ja)} en={len(en)}")
    if [p.parent.name for p in ja] != [p.parent.name for p in en]:
        fail("locale slug sets differ")

    required = ['rel="canonical"', 'hreflang="ja"', 'hreflang="en"', 'hreflang="x-default"', '"@type":"TouristAttraction"', '"@type":"BreadcrumbList"', 'name="twitter:card" content="summary_large_image"']
    for language, pages in (("ja", ja), ("en", en)):
        titles = set()
        meta_descriptions = set()
        for path in pages:
            text = path.read_text(encoding="utf-8")
            missing = [value for value in required if value not in text]
            if missing:
                fail(f"{path.relative_to(ROOT)} missing {missing}")
            head = text.split("</head>", 1)[0]
            if re.search(r"UNESCO", head, re.I):
                fail(f"{path.relative_to(ROOT)} uses UNESCO in SEO metadata")
            if any(description in text for description in descriptions):
                fail(f"{path.relative_to(ROOT)} reproduces a source description")
            title = html.unescape(re.search(r"<title>(.*?)</title>", text, re.S).group(1))
            meta = html.unescape(re.search(r'<meta name="description" content="([^"]*)">', text).group(1))
            if title in titles or meta in meta_descriptions:
                fail(f"{path.relative_to(ROOT)} has duplicate title or meta description")
            if len(meta) > 155:
                fail(f"{path.relative_to(ROOT)} meta description exceeds 155 characters")
            titles.add(title)
            meta_descriptions.add(meta)
            match = re.search(r'<script type="application/ld\+json">(.*?)</script>', text, re.S)
            try:
                json.loads(match.group(1) if match else "")
            except json.JSONDecodeError as exc:
                fail(f"{path.relative_to(ROOT)} invalid JSON-LD: {exc}")
            for href in re.findall(r'href="([^"]+)"', text):
                parsed = urlsplit(href.replace("&amp;", "&"))
                if parsed.scheme or parsed.netloc or not parsed.path or parsed.path.startswith("/"):
                    continue
                target = (path.parent / unquote(parsed.path)).resolve()
                if target.is_dir():
                    target /= "index.html"
                if not target.exists():
                    fail(f"{path.relative_to(ROOT)} broken link: {href}")

    for path in (ROOT / "items/index.html", ROOT / "en/items/index.html"):
        text = path.read_text(encoding="utf-8")
        if text.count('<li><a href="') != EXPECTED:
            fail(f"{path.relative_to(ROOT)} index count mismatch")
        if any(description in text for description in descriptions):
            fail(f"{path.relative_to(ROOT)} reproduces a source description")

    root = ET.parse(ROOT / "sitemap.xml").getroot()
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    urls = [n.text for n in root.findall("s:url/s:loc", ns)]
    if len(urls) != EXPECTED * 2 + 8 or len(urls) != len(set(urls)):
        fail(f"invalid sitemap URL set: {len(urls)}")
    robots = (ROOT / "robots.txt").read_text(encoding="utf-8")
    if "https://kimuhixy.com/world-heritage-globe/sitemap.xml" not in robots:
        fail("robots.txt sitemap missing")
    print(f"Validated {len(ja) + len(en):,} fact-only detail pages, 2 indexes, and {len(urls):,} sitemap URLs.")


if __name__ == "__main__":
    main()
