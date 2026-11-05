#!/usr/bin/env python3
"""fit_image.py — 把生成的點陣圖修成「能用的尺寸」

為什麼需要這支腳本（都是實際踩到的坑）：
  1. 繪圖模型不一定照 prompt 的比例走。你說 16:9，它給你 1:1。
  2. Cherry Studio 生成的圖右下角會多一個「AI生成」浮水印。
這支腳本用 headless 瀏覽器做 cover 裁切，一次解決這兩件事：
  --zoom 放大一點 → 把邊緣（連同浮水印）切掉；--position 決定留住哪一角。

用法：
    # 把 2048×2048 的生成圖裁成 1920×1080，並把右下角浮水印切掉
    python fit_image.py hero.jpg -o hero-1920x1080.jpg --size 1920x1080 \
        --zoom 1.09 --position "0% 0%"

    # 只改比例、不動內容
    python fit_image.py hero.jpg -o hero.png --size 1920x1080

    # 一次輸出多個尺寸
    python fit_image.py hero.jpg -o out/ --sizes 1920x1080,1280x720,1080x1920
"""

from __future__ import annotations

import argparse
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from export_png import find_browser, screenshot_html  # noqa: E402

SIZE_RE = re.compile(r"^\s*(\d+)\s*[x×]\s*(\d+)\s*$")


def parse_sizes(raw: str) -> list[tuple[int, int]]:
    out = []
    for part in raw.split(","):
        m = SIZE_RE.match(part)
        if not m:
            raise SystemExit(f"尺寸格式要像 1920x1080，收到：{part!r}")
        out.append((int(m.group(1)), int(m.group(2))))
    return out


def build_html(src: Path, width: int, height: int, zoom: float, position: str, bg: str) -> str:
    """用 <img> + object-fit:cover 做裁切，zoom 用 transform:scale。

    不用 JS 算尺寸——截圖可能比 onload 早一步。純 CSS 是同步且可預期的。
    """
    origin = {"center": "50% 50%", "left top": "0% 0%", "top left": "0% 0%",
              "left bottom": "0% 100%", "right top": "100% 0%",
              "right bottom": "100% 100%"}.get(position, position)
    return (
        "<!DOCTYPE html><html><head><meta charset=\"utf-8\"><style>"
        "html,body{margin:0;padding:0;background:" + (bg or "transparent") + "}"
        f".box{{width:{width}px;height:{height}px;overflow:hidden;position:relative}}"
        ".box img{position:absolute;inset:0;width:100%;height:100%;"
        f"object-fit:cover;transform:scale({zoom});transform-origin:{origin}}}"
        f"</style></head><body><div class=\"box\"><img src=\"{src.as_uri()}\"></div></body></html>"
    )


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    ap = argparse.ArgumentParser(description="把生成的圖片裁成指定尺寸（cover）")
    ap.add_argument("src", help="來源圖片（jpg／png／webp）")
    ap.add_argument("-o", "--out", required=True, help="輸出檔案，或（多尺寸時）輸出資料夾")
    ap.add_argument("--size", default="", help="單一尺寸，例如 1920x1080")
    ap.add_argument("--sizes", default="", help="多個尺寸，逗號分隔，例如 1920x1080,1280x720")
    ap.add_argument("--zoom", type=float, default=1.0, help="放大倍率，>1 會把邊緣切掉（去浮水印用 1.05～1.12）")
    ap.add_argument("--position", default="center", help="留住的位置，例如 '0%% 0%%'（左上）、'right bottom'、'center'")
    ap.add_argument("--bg", default="#000000", help="留白處的底色（cover 裁切通常不會用到）")
    args = ap.parse_args()

    src = Path(args.src)
    if not src.exists():
        print(f"找不到來源圖片：{src}")
        return 2

    if args.sizes:
        size_list = parse_sizes(args.sizes)
    elif args.size:
        size_list = parse_sizes(args.size)
    else:
        print("請用 --size 1920x1080 或 --sizes 1920x1080,1280x720 指定尺寸")
        return 2

    exe = find_browser()
    if not exe:
        print("找不到 Chrome／Edge，無法裁圖。請改用其他影像工具，或安裝 resvg 以外的瀏覽器。")
        return 3

    out_arg = Path(args.out)
    multi = len(size_list) > 1 or not out_arg.suffix
    if multi:
        out_arg.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="fitimg-") as tmp:
        profile = Path(tmp) / "profile"
        for w, h in size_list:
            target = (out_arg / f"{src.stem}-{w}x{h}{src.suffix}") if multi else out_arg
            target.parent.mkdir(parents=True, exist_ok=True)
            html = build_html(src, w, h, args.zoom, args.position, args.bg)
            screenshot_html(html, target, w, h, exe, profile, "00000000")
            print(f"  {target}  ({w}x{h})")

    print(f"\n完成：{src.name} → {len(size_list)} 個尺寸")
    print("記得開起來確認：浮水印有沒有切乾淨、主體有沒有被切到。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
