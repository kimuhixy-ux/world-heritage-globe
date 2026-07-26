#!/usr/bin/env python3
"""PWA用アイコン(icons/icon-192.png, icon-512.png)を生成するスクリプト。

夜空に浮かぶ地球と、世界遺産を表す金色の光点をシンプルに描画する。
再実行すれば同じデザインで再生成できる。

使い方:
  python3 scripts/generate_icons.py
"""

import math
import random
from pathlib import Path

from PIL import Image, ImageDraw

SCRIPT_DIR = Path(__file__).resolve().parent
ICONS_DIR = SCRIPT_DIR.parent / "icons"

BG_TOP = (5, 7, 15)
BG_BOTTOM = (10, 14, 28)
GLOBE_DARK = (13, 30, 58)
GLOBE_LIGHT = (30, 70, 110)
GOLD = (244, 201, 93)
GREEN = (111, 208, 140)
BLUE = (95, 180, 239)

random.seed(42)


def draw_icon(size):
    img = Image.new("RGB", (size, size), BG_TOP)
    draw = ImageDraw.Draw(img)

    # 背景: 上から下へのグラデーション
    for y in range(size):
        t = y / size
        r = round(BG_TOP[0] + (BG_BOTTOM[0] - BG_TOP[0]) * t)
        g = round(BG_TOP[1] + (BG_BOTTOM[1] - BG_TOP[1]) * t)
        b = round(BG_TOP[2] + (BG_BOTTOM[2] - BG_TOP[2]) * t)
        draw.line([(0, y), (size, y)], fill=(r, g, b))

    center = size / 2
    radius = size * 0.36

    # 地球本体: 中心から縁へのグラデーション(球体感を出す)
    steps = 60
    for i in range(steps, 0, -1):
        t = i / steps
        r = radius * t
        cx = center - radius * 0.28
        cy = center - radius * 0.28
        col = tuple(
            round(GLOBE_LIGHT[c] + (GLOBE_DARK[c] - GLOBE_LIGHT[c]) * (1 - t))
            for c in range(3)
        )
        draw.ellipse(
            [center - r, center - r, center + r, center + r],
            fill=col,
        )

    # 世界遺産の光点をランダムに散らす
    colors = [GOLD, GOLD, GOLD, GREEN, BLUE]
    dot_r = max(2, round(size * 0.014))
    placed = 0
    attempts = 0
    while placed < 26 and attempts < 500:
        attempts += 1
        angle = random.uniform(0, 2 * math.pi)
        dist = random.uniform(0, radius * 0.88)
        x = center + math.cos(angle) * dist
        y = center + math.sin(angle) * dist
        col = random.choice(colors)
        draw.ellipse([x - dot_r, y - dot_r, x + dot_r, y + dot_r], fill=col)
        placed += 1

    # 大気の光彩(縁を淡く光らせる)
    glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    glow_draw.ellipse(
        [
            center - radius * 1.08,
            center - radius * 1.08,
            center + radius * 1.08,
            center + radius * 1.08,
        ],
        outline=(95, 180, 239, 120),
        width=max(2, round(size * 0.012)),
    )
    img = Image.alpha_composite(img.convert("RGBA"), glow).convert("RGB")

    return img


def main():
    ICONS_DIR.mkdir(parents=True, exist_ok=True)
    for size in (192, 512):
        icon = draw_icon(size)
        out_path = ICONS_DIR / f"icon-{size}.png"
        icon.save(out_path)
        print(f"生成しました: {out_path}")


if __name__ == "__main__":
    main()
