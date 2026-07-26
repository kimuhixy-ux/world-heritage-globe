#!/usr/bin/env python3
"""地球儀のテクスチャ(img/earth-day.jpg)を生成するスクリプト。

NASA公開(パブリックドメイン)の実写衛星画像を合成する。
- Blue Marble (陸地・地形): NASA Visible Earth
- Black Marble (夜間光): NASA Visible Earth / Suomi NPP VIIRS
昼間の地形の上に、都市部の光だけを暖色でスクリーン合成して重ねている。

ネットワーク接続が必要。生成結果はリポジトリにコミット済みなので、
テクスチャを作り直したい場合のみ実行すればよい。

使い方:
  python3 scripts/generate_earth_texture.py
"""

import urllib.request
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops

Image.MAX_IMAGE_PIXELS = None

SCRIPT_DIR = Path(__file__).resolve().parent
IMG_DIR = SCRIPT_DIR.parent / "img"

BLUE_MARBLE_URL = (
    "https://eoimages.gsfc.nasa.gov/images/imagerecords/73000/73909/"
    "world.topo.bathy.200412.3x21600x10800.jpg"
)
BLACK_MARBLE_URL = (
    "https://eoimages.gsfc.nasa.gov/images/imagerecords/79000/79765/"
    "dnb_land_ocean_ice.2012.13500x6750.jpg"
)

OUT_SIZE = (16384, 8192)
CITY_LIGHT_THRESHOLD = 70.0  # これ未満の輝度は都市の光とみなさず捨てる(海上のノイズ除去のため引き上げ)


def download(url, dest):
    if not dest.exists():
        print(f"ダウンロード中: {url}")
        urllib.request.urlretrieve(url, dest)
    return Image.open(dest)


def main():
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    tmp_dir = SCRIPT_DIR / ".texture_cache"
    tmp_dir.mkdir(exist_ok=True)

    day = download(BLUE_MARBLE_URL, tmp_dir / "blue_marble.jpg").convert("RGB").resize(OUT_SIZE, Image.LANCZOS)
    night = download(BLACK_MARBLE_URL, tmp_dir / "black_marble.jpg").convert("L").resize(OUT_SIZE, Image.LANCZOS)

    night_arr = np.asarray(night, dtype=np.float32)
    mask = np.clip(
        (night_arr - CITY_LIGHT_THRESHOLD) * (255.0 / (255.0 - CITY_LIGHT_THRESHOLD)), 0, 255
    )
    city_lights = Image.merge(
        "RGB",
        [
            Image.fromarray(mask.astype("uint8")),
            Image.fromarray((mask * 0.75).astype("uint8")),
            Image.fromarray((mask * 0.35).astype("uint8")),
        ],
    )

    composite = ImageChops.screen(day, city_lights)
    out_path = IMG_DIR / "earth-day.jpg"
    composite.save(out_path, quality=85, optimize=True)
    print(f"生成しました: {out_path}")


if __name__ == "__main__":
    main()
