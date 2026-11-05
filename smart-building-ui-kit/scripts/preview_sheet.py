#!/usr/bin/env python3
"""preview_sheet.py — 產生圖示驗收頁（preview.html）與清單（manifest.json）

用法：
    python preview_sheet.py icons/ -o . --tokens tokens.css
    python preview_sheet.py icons/ -o . --title "寶麒中控圖示集 v1"

為什麼要有這頁：lint 全綠不代表看起來對。圖示是給眼睛用的東西，
一定要把同一顆圖示並排在淺色底、深色底、五種狀態色、四種尺寸下看過，
才會發現「這顆太密」「那顆線條比別人粗」這種問題。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

DEFAULT_TOKENS = {
    "icon-ink": "#1F2A37",
    "icon-ink-muted": "#8FA3B8",
    "state-online": "#30A46C",
    "state-active": "#2AA9E0",
    "state-warning": "#F5A524",
    "state-alarm": "#E5484D",
    "state-offline": "#5A6B7D",
    "icon-accent": "#2AA9E0",
    "surface-deep": "#0A111B",
    "surface-panel": "#0E1622",
    "surface-card": "#141E2C",
    "hairline": "#22303F",
}

SIZES = (24, 32, 48, 64)
STATES = ("state-online", "state-active", "state-warning", "state-alarm", "state-offline")


def load_tokens(css: Path | None) -> dict[str, str]:
    tokens = dict(DEFAULT_TOKENS)
    if css and css.exists():
        text = css.read_text(encoding="utf-8")
        blocks = [("", re.search(r":root\s*\{(.*?)\}", text, re.S))]
        blocks.append(("dark-", re.search(r'\[data-theme="dark"\]\s*\{(.*?)\}', text, re.S)))
        for prefix, m in blocks:
            if not m:
                continue
            for name, val in re.findall(r"--([\w-]+)\s*:\s*([^;]+);", m.group(1)):
                tokens[prefix + name] = val.strip()
    return tokens


def strip_xml_decl(svg: str) -> str:
    return re.sub(r"<\?xml.*?\?>|<!DOCTYPE.*?>", "", svg, flags=re.S).strip()


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="產生圖示驗收頁")
    ap.add_argument("icons", help="圖示資料夾")
    ap.add_argument("-o", "--out", default=".", help="輸出資料夾（放 preview.html 與 manifest.json）")
    ap.add_argument("--tokens", default="", help="tokens.css 路徑（讀出實際色票）")
    ap.add_argument("--title", default="智慧建築圖示集", help="頁面標題")
    ap.add_argument("--manifest", default="manifest.json", help="清單檔名")
    args = ap.parse_args()

    icon_dir = Path(args.icons)
    files = sorted(icon_dir.glob("*.svg"))
    if not files:
        print(f"找不到任何 .svg 檔：{icon_dir}")
        return 2

    tokens = load_tokens(Path(args.tokens) if args.tokens else None)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        rel_icon_dir = icon_dir.resolve().relative_to(out_dir.resolve())
    except ValueError:
        rel_icon_dir = icon_dir

    cards, manifest = [], []
    for f in files:
        svg = strip_xml_decl(f.read_text(encoding="utf-8"))
        manifest.append(
            {
                "name": f.stem,
                "file": str((rel_icon_dir / f.name).as_posix()),
                "bytes": f.stat().st_size,
                "sha256": hashlib.sha256(f.read_bytes()).hexdigest()[:12],
            }
        )

        def cell(label: str, color: str, size: int, cls: str = "") -> str:
            return (
                f'<div class="cell {cls}"><div class="lbl">{label}</div>'
                f'<div class="icon" style="color:{color};width:{size}px;height:{size}px">{svg}</div></div>'
            )

        light = "".join(cell(f"淺 {s}", tokens["icon-ink"], s, "on-light") for s in SIZES[:3])
        dark = "".join(cell(f"深 {s}", tokens["dark-icon-ink"], s, "on-dark") for s in SIZES[:3])
        states = "".join(
            cell(k.replace("state-", ""), tokens[k], 32, "on-light") for k in STATES
        )
        cards.append(
            f'<article class="card"><header><h3>{f.stem}</h3>'
            f'<code>{rel_icon_dir.as_posix()}/{f.name}</code></header>'
            f'<div class="row">{light}{dark}</div>'
            f'<div class="row states">{states}</div>'
            f"</article>"
        )

    html = TEMPLATE
    for key, val in {
        "__TITLE__": args.title,
        "__COUNT__": str(len(files)),
        "__DATE__": "",
        "__TOKENS__": "\n".join(f"  --{k}: {v};" for k, v in tokens.items() if not k.startswith("dark-")),
        "__DARK_TOKENS__": "\n".join(
            f"  --{k[5:]}: {v};" for k, v in tokens.items() if k.startswith("dark-")
        ),
        "__SURFACE__": tokens["surface-deep"],
        "__PANEL__": tokens["surface-panel"],
        "__CARD__": tokens["surface-card"],
        "__HAIRLINE__": tokens["hairline"],
        "__CARDS__": "\n".join(cards),
    }.items():
        html = html.replace(key, val)

    preview = out_dir / "preview.html"
    preview.write_text(html, encoding="utf-8")
    manifest_path = out_dir / args.manifest
    manifest_path.write_text(json.dumps({"icons": manifest}, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"已產生 {preview}（{len(files)} 顆圖示）")
    print(f"已產生 {manifest_path}")
    print("請開起來看過再往下走：同一顆圖示在深淺底色與五種狀態色下都要讀得出來。")
    return 0


TEMPLATE = """<!DOCTYPE html>
<html lang="zh-Hant" data-theme="light">
<head>
<meta charset="utf-8">
<title>__TITLE__ — 圖示驗收</title>
<style>
  :root {
__TOKENS__
  }
  [data-theme="dark"] {
__DARK_TOKENS__
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; padding: 32px;
    background: __SURFACE__; color: #E6EDF5;
    font: 14px/1.6 "Segoe UI", "Noto Sans TC", system-ui, sans-serif;
  }
  h1 { margin: 0 0 4px; font-size: 22px; font-weight: 600; }
  .sub { color: #7C8EA3; margin-bottom: 24px; }
  .grid { display: grid; gap: 16px; grid-template-columns: repeat(auto-fill, minmax(420px, 1fr)); }
  .card { background: __PANEL__; border: 1px solid __HAIRLINE__; border-radius: 10px; overflow: hidden; }
  .card header { padding: 12px 14px; border-bottom: 1px solid __HAIRLINE__; }
  .card h3 { margin: 0; font-size: 14px; font-weight: 600; color: #E6EDF5; }
  .card code { color: #7C8EA3; font-size: 11px; }
  .row { display: flex; flex-wrap: wrap; }
  .cell { display: flex; flex-direction: column; align-items: center; gap: 6px; padding: 14px 16px; }
  .cell.on-light { background: #FFFFFF; }
  .cell.on-dark { background: __PANEL__; }
  .cell.states, .row.states .cell { border-top: 1px solid __HAIRLINE__; }
  .lbl { font-size: 10px; letter-spacing: .04em; color: #8FA3B8; text-transform: uppercase; }
  .cell.on-light .lbl { color: #8FA3B8; }
  .icon svg { width: 100%; height: 100%; display: block; }
</style>
</head>
<body>
  <h1>__TITLE__</h1>
  <div class="sub">__COUNT__ 顆圖示 · 淺色底／深色底／五種狀態色並排檢查</div>
  <div class="grid">
__CARDS__
  </div>
</body>
</html>
"""


if __name__ == "__main__":
    sys.exit(main())
