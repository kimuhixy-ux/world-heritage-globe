#!/usr/bin/env python3
"""
UNESCO世界遺産リストのXMLをアプリ用のdata/heritage.jsonに変換するスクリプト。

【再取得の手順】
公式サイト https://whc.unesco.org/en/list/xml はCloudflareのボット保護が
かかっており、requests/urllibで直接ダウンロードすると403になる。
毎年の新規登録に対応して再生成したいときは、以下の手順で
whc_list.xml を新しくしてから、このスクリプトを再実行する。

  1. 実際のブラウザ(Chrome等)で https://whc.unesco.org/en/list/xml を開く
  2. ページ全体を保存(サイト内容をコピーしてテキストファイルとして保存でも可)
  3. scripts/whc_list.xml として上書き保存
  4. `python3 scripts/build_data.py` を実行 → data/heritage.json が更新される

使い方:
  python3 scripts/build_data.py
"""

import json
import re
import statistics
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
XML_PATH = SCRIPT_DIR / "whc_list.xml"
OUTPUT_PATH = SCRIPT_DIR.parent / "data" / "heritage.json"

DESCRIPTION_MAX_LEN = 200


def strip_html(text):
    """短い説明文からHTMLタグを除去し、空白を正規化する。"""
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("&nbsp;", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def truncate(text, max_len=DESCRIPTION_MAX_LEN):
    if len(text) <= max_len:
        return text
    # 単語の途中で切らないよう、直前のスペースまで戻る
    cut = text[:max_len]
    last_space = cut.rfind(" ")
    if last_space > max_len * 0.6:
        cut = cut[:last_space]
    return cut.rstrip(",.;:") + "…"


def average_coords(row):
    """複数国にまたがる遺産(transboundary)は複数poiの重心を1点として採用する。"""
    lats, lngs = [], []
    for poi in row.findall("./geolocations/poi"):
        lat = poi.findtext("latitude")
        lng = poi.findtext("longitude")
        if lat and lng:
            lats.append(float(lat))
            lngs.append(float(lng))
    if not lats:
        return None, None
    return statistics.mean(lats), statistics.mean(lngs)


def build_youtube_search_url(name):
    query = f"{name} UNESCO World Heritage"
    return "https://www.youtube.com/results?search_query=" + urllib.parse.quote(query)


def build_record(row):
    id_number = row.findtext("id_number", "").strip()
    name = strip_html(row.findtext("site", ""))
    country = (row.findtext("states", "") or "").replace(",", ", ")
    region = row.findtext("regions", "") or ""
    category = row.findtext("category", "") or ""
    year_text = row.findtext("date_inscribed", "") or ""
    danger_text = (row.findtext("danger", "") or "").strip()
    description = truncate(strip_html(row.findtext("short_description", "")))

    lat, lng = average_coords(row)
    if lat is None:
        return None

    try:
        year = int(year_text)
    except ValueError:
        year = None

    return {
        "id": id_number,
        "name": name,
        "country": country,
        "region": region,
        "category": category,
        "lat": round(lat, 4),
        "lng": round(lng, 4),
        "year": year,
        "danger": bool(danger_text),
        "url": f"https://whc.unesco.org/en/list/{id_number}",
        "description": description,
        "youtube_search_url": build_youtube_search_url(name),
    }


def main():
    if not XML_PATH.exists():
        raise SystemExit(
            f"エラー: {XML_PATH} が見つかりません。"
            "先に公式サイトのXMLをブラウザで取得して配置してください(このファイル冒頭のコメント参照)。"
        )

    tree = ET.parse(XML_PATH)
    rows = tree.getroot().findall("row")

    records = []
    skipped = 0
    for row in rows:
        record = build_record(row)
        if record is None:
            skipped += 1
            continue
        records.append(record)

    records.sort(key=lambda r: (r["year"] or 0, r["id"]))

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    json_text = json.dumps(records, ensure_ascii=False, separators=(",", ":"))
    OUTPUT_PATH.write_text(json_text, encoding="utf-8")

    size_kb = len(json_text.encode("utf-8")) / 1024
    print(f"{len(records)}件を変換しました(座標なしで除外: {skipped}件)")
    print(f"出力: {OUTPUT_PATH} ({size_kb:.1f} KB)")
    if size_kb > 1500:
        print("警告: JSONサイズが1.5MBを超えています。descriptionの短縮を検討してください。")


if __name__ == "__main__":
    main()
