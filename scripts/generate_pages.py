#!/usr/bin/env python3
"""Generate bilingual fact-only heritage pages without source descriptions."""

from __future__ import annotations

import html
import json
import re
import shutil
import unicodedata
from collections import defaultdict
from pathlib import Path
from string import Template
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://kimuhixy.com/world-heritage-globe"
OG_IMAGE = f"{BASE}/icons/icon-512.png"
CATEGORY_JA = {"Cultural": "文化遺産", "Natural": "自然遺産", "Mixed": "複合遺産"}
REGION_JA = {
    "Africa": "アフリカ", "Arab States": "アラブ諸国", "Asia and the Pacific": "アジア・太平洋",
    "Europe and North America": "ヨーロッパ・北米", "Latin America and the Caribbean": "中南米・カリブ海",
    "Multiple": "複数地域", "": "その他",
}


def region_label(region: str, english: bool) -> str:
    if english:
        return region
    return "・".join(REGION_JA.get(part.strip(), part.strip()) for part in region.split(","))


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def load_data() -> list[dict]:
    records = json.loads((ROOT / "data/heritage.json").read_text(encoding="utf-8"))
    required = {"id", "name", "nameJa", "country", "countryJa", "region", "category", "lat", "lng", "year", "danger", "url", "youtube_search_url"}
    for i, record in enumerate(records, 1):
        missing = required - record.keys()
        if missing:
            raise ValueError(f"record {i} missing {sorted(missing)}")
    return records


def slugify(record: dict) -> str:
    normalized = unicodedata.normalize("NFKD", record["name"]).encode("ascii", "ignore").decode().lower()
    name = re.sub(r"[^a-z0-9]+", "-", normalized).strip("-") or "site"
    return f'{record["id"]}-{name}'


def related_indices(records: list[dict]) -> list[list[int]]:
    result = []
    for i, item in enumerate(records):
        ranked = sorted(
            (j for j in range(len(records)) if j != i),
            key=lambda j: (
                -(records[j]["country"] == item["country"]),
                -(records[j]["region"] == item["region"]),
                -(records[j]["category"] == item["category"]),
                abs(records[j]["year"] - item["year"]),
                records[j]["name"].casefold(),
            ),
        )
        result.append(ranked[:6])
    return result


def fact(label: str, value: object) -> str:
    return f"<div><dt>{esc(label)}</dt><dd>{esc(value)}</dd></div>"


def metadata_description(item: dict, english: bool) -> str:
    if english:
        danger = " Currently listed as in danger." if item["danger"] else ""
        text = f'{item["name"]} in {item["country"]}: {item["category"].lower()} World Heritage site, inscribed in {item["year"]}.{danger}'
        return text if len(text) <= 155 else text[:154].rstrip() + "…"
    danger = "現在は危機遺産です。" if item["danger"] else ""
    text = f'{item["nameJa"]}（{item["countryJa"]}）は{item["year"]}年登録の{CATEGORY_JA[item["category"]]}です。{danger}'
    return text if len(text) <= 155 else text[:154].rstrip() + "…"


def schema(item: dict, slug: str, english: bool) -> str:
    lang = "en" if english else "ja"
    prefix = "en/" if english else ""
    canonical = f"{BASE}/{prefix}items/{slug}/"
    name = item["name"] if english else item["nameJa"]
    country = item["country"] if english else item["countryJa"]
    graph = {
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "WebSite", "@id": f"{BASE}/#website", "url": f"{BASE}/", "name": "World Heritage Globe" if english else "世界遺産グローブ", "inLanguage": ["ja", "en"]},
            {"@type": "TouristAttraction", "@id": f"{canonical}#place", "name": name, "alternateName": item["nameJa"] if english else item["name"], "url": canonical, "inLanguage": lang,
             "geo": {"@type": "GeoCoordinates", "latitude": item["lat"], "longitude": item["lng"]},
             "address": {"@type": "PostalAddress", "addressCountry": country},
             "additionalProperty": [
                 {"@type": "PropertyValue", "name": "Category", "value": item["category"]},
                 {"@type": "PropertyValue", "name": "Inscription year", "value": item["year"]},
                 {"@type": "PropertyValue", "name": "Region", "value": item["region"]},
                 {"@type": "PropertyValue", "name": "In danger", "value": item["danger"]},
             ]},
            {"@type": "BreadcrumbList", "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Home" if english else "トップ", "item": f"{BASE}/{prefix}"},
                {"@type": "ListItem", "position": 2, "name": "Site index" if english else "世界遺産索引", "item": f"{BASE}/{prefix}items/"},
                {"@type": "ListItem", "position": 3, "name": name, "item": canonical},
            ]},
        ],
    }
    return json.dumps(graph, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def detail_context(item: dict, slug: str, related: list[int], records: list[dict], slugs: list[str], english: bool) -> dict[str, str]:
    name = item["name"] if english else item["nameJa"]
    country = item["country"] if english else item["countryJa"]
    region = region_label(item["region"], english)
    category = item["category"] if english else CATEGORY_JA[item["category"]]
    danger = "Yes" if item["danger"] else "No"
    if not english:
        danger = "該当" if item["danger"] else "非該当"
    labels = ("Country", "Region", "Inscription year", "In danger", "Coordinates") if english else ("所在国", "地域", "登録年", "危機遺産", "位置")
    facts = fact(labels[0], country) + fact(labels[1], region) + fact(labels[2], item["year"]) + fact(labels[3], danger) + fact(labels[4], f'{item["lat"]}, {item["lng"]}')
    links = "".join(
        f'<li><a href="../{slugs[i]}/">{esc(records[i]["name"] if english else records[i]["nameJa"])}</a><span>{esc(records[i]["country"] if english else records[i]["countryJa"])}</span></li>'
        for i in related
    )
    heading = "Related sites" if english else "関連する世界遺産"
    related_html = f'<section class="related-section"><h2>{heading}</h2><ul>{links}</ul></section>'
    prefix = "en/" if english else ""
    return {
        "slug": slug, "title": esc(name), "page_title": esc((f'{name} – {country} ({item["year"]}) | World Heritage Site Facts') if english else f'{name}（{country}・{item["year"]}年）| 世界遺産データ'),
        "meta_description": esc(metadata_description(item, english)), "canonical": f"{BASE}/{prefix}items/{slug}/",
        "ja_url": f"{BASE}/items/{slug}/", "en_url": f"{BASE}/en/items/{slug}/", "og_image": OG_IMAGE,
        "json_ld": schema(item, slug, english), "category_label": esc(category), "facts": facts,
        "app_url": ("../../../en/" if english else "../../") + "?id=" + quote(str(item["id"])),
        "source_url": esc(item["url"]), "youtube_url": esc(item["youtube_search_url"]), "related": related_html,
    }


def index_groups(records: list[dict], slugs: list[str], english: bool) -> str:
    grouped: dict[str, dict[str, list[tuple[str, str, int]]]] = defaultdict(lambda: defaultdict(list))
    for item, slug in zip(records, slugs):
        region = region_label(item["region"], english)
        country = item["country"] if english else item["countryJa"]
        name = item["name"] if english else item["nameJa"]
        grouped[region][country].append((name, slug, item["year"]))
    sections = []
    for region in sorted(grouped):
        countries = []
        for country in sorted(grouped[region]):
            sites = "".join(f'<li><a href="{slug}/">{esc(name)}</a><span>{year}</span></li>' for name, slug, year in sorted(grouped[region][country], key=lambda x: x[0]))
            countries.append(f'<section class="country-group"><h3>{esc(country)}</h3><ul>{sites}</ul></section>')
        sections.append(f'<section class="region-group"><h2>{esc(region)}</h2>{"".join(countries)}</section>')
    return "".join(sections)


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def main() -> None:
    records = load_data()
    slugs = [slugify(item) for item in records]
    if len(slugs) != len(set(slugs)):
        raise ValueError("duplicate slugs")
    related = related_indices(records)
    templates = {name: Template((ROOT / f"templates/{name}.html").read_text(encoding="utf-8")) for name in ("detail_ja", "detail_en", "index_ja", "index_en")}
    for directory in (ROOT / "items", ROOT / "en/items"):
        if directory.exists():
            shutil.rmtree(directory)
    for i, (item, slug) in enumerate(zip(records, slugs)):
        write(ROOT / "items" / slug / "index.html", templates["detail_ja"].substitute(detail_context(item, slug, related[i], records, slugs, False)))
        write(ROOT / "en/items" / slug / "index.html", templates["detail_en"].substitute(detail_context(item, slug, related[i], records, slugs, True)))
    common = {"ja_url": f"{BASE}/items/", "en_url": f"{BASE}/en/items/"}
    write(ROOT / "items/index.html", templates["index_ja"].substitute(common, groups=index_groups(records, slugs, False)))
    write(ROOT / "en/items/index.html", templates["index_en"].substitute(common, groups=index_groups(records, slugs, True)))
    urls = [f"{BASE}/", f"{BASE}/en/", f"{BASE}/about.html", f"{BASE}/en/about.html", f"{BASE}/privacy.html", f"{BASE}/en/privacy.html", f"{BASE}/items/", f"{BASE}/en/items/"]
    urls += [f"{BASE}/items/{slug}/" for slug in slugs] + [f"{BASE}/en/items/{slug}/" for slug in slugs]
    sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "".join(f"  <url><loc>{html.escape(url)}</loc></url>\n" for url in urls) + "</urlset>\n"
    write(ROOT / "sitemap.xml", sitemap)
    write(ROOT / "robots.txt", f"User-agent: *\nAllow: /\n\nSitemap: {BASE}/sitemap.xml\n")
    print(f"Generated {len(records) * 2:,} detail pages, 2 indexes, and {len(urls):,} sitemap URLs.")


if __name__ == "__main__":
    main()
