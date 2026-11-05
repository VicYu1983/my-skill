#!/usr/bin/env python3
"""svg_lint.py — 智慧建築圖示規格檢查

用法：
    python svg_lint.py icons/
    python svg_lint.py icons/ --json
    python svg_lint.py icons/ --strict      # warning 也算失敗（CI 用）

檢查的是「會壞掉」與「會不一致」兩類問題：
  E1 檔名不符 <domain>-<name>.svg      ← 找不到、無法分類
  E2 viewBox 不是 "0 0 24 24"          ← 尺寸不統一，橫豎比會跑掉
  E3 根元素缺 fill="none" 或 stroke="currentColor"  ← 換不了狀態色
  E4 寫死顏色（#hex / rgb() / hsl()）  ← 深淺主題與狀態色全部失效
  E5 使用 <image> <text> <filter> <foreignObject>   ← 糊掉、缺字型、特效髒
  E6 幾何超出 0..24 畫布               ← 被裁掉
  W1 幾何超出 2..22 安全區             ← 在底色塊上會黏邊
  W2 stroke-width 不是 2（或不在建議值）← 一排圖示看起來像拼裝
  W3 缺少 round 的線端／接角           ← 深色底出現灰點
  W4 class="accent" 沒配 var(--icon-accent, …)      ← 雙色調機制壞掉
  W5 根元素寫了 width/height           ← 蓋掉 CSS 縮放
  W6 出現 <style> 或 style="…"         ← 會和外部主題打架
  W7 其他（BOM、漸層、缺 xmlns）
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

DOMAINS = ("dev", "sec", "mep", "nrg", "sens", "ctrl", "nav", "sts")
NAME_RE = re.compile(r"^(?:" + "|".join(DOMAINS) + r")-[a-z0-9]+(?:-[a-z0-9]+)*\.svg$")
HEX_RE = re.compile(r"#[0-9a-fA-F]{3,8}\b")
FUNC_RE = re.compile(r"\b(?:rgba?|hsla?)\s*\([^)]*\)")
ALLOWED_STROKES = (1.0, 1.5, 2.0, 2.5, 3.0)
GEO_ATTRS = ("x", "y", "x1", "y1", "x2", "y2", "cx", "cy", "r", "rx", "ry", "width", "height", "points", "d")
ATTR_RE = re.compile(r'(?<![\w-])(' + "|".join(GEO_ATTRS) + r')\s*=\s*"([^"]*)"')
NUM_RE = re.compile(r"-?\d+(?:\.\d+)?")
SIZE_ATTRS = ("r", "rx", "ry")   # 這些是尺寸不是位置，不受 2..22 安全區限制
ARGC = {"m": 2, "l": 2, "h": 1, "v": 1, "c": 6, "s": 4, "q": 4, "t": 2, "a": 7, "z": 0}
PATH_TOKEN_RE = re.compile(r"[MmLlHhVvCcSsQqTtAaZz]|-?\d*\.?\d+(?:[eE]-?\d+)?")


def path_points(d: str) -> list[tuple[float, float]]:
    """把 path 的 d 解成絕對座標點（含控制點）。

    為什麼要自己解：d 裡的相對指令（h16、l3.5-3.5）看起來像負數或超界數字，
    直接抓數字會誤判。這裡照指令累加，才能真正問「這個圖有沒有畫出畫布」。
    """
    tokens = PATH_TOKEN_RE.findall(d)
    pts: list[tuple[float, float]] = []
    x = y = 0.0
    sx = sy = 0.0
    cmd: str | None = None
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok.isalpha():
            cmd = tok
            i += 1
            if cmd in "Zz":
                x, y = sx, sy
                pts.append((x, y))
            continue
        if cmd is None:
            i += 1
            continue
        low = cmd.lower()
        need = ARGC.get(low, 0)
        if need == 0:
            i += 1
            continue
        args: list[float] = []
        while len(args) < need and i < len(tokens) and not tokens[i].isalpha():
            args.append(float(tokens[i]))
            i += 1
        if len(args) < need:
            break
        rel = cmd.islower()
        if low == "m":
            x = x + args[0] if rel else args[0]
            y = y + args[1] if rel else args[1]
            sx, sy = x, y
            pts.append((x, y))
            cmd = "l" if rel else "L"       # M 之後的座標對視為 lineto
        elif low == "l":
            x = x + args[0] if rel else args[0]
            y = y + args[1] if rel else args[1]
            pts.append((x, y))
        elif low == "h":
            x = x + args[0] if rel else args[0]
            pts.append((x, y))
        elif low == "v":
            y = y + args[0] if rel else args[0]
            pts.append((x, y))
        elif low in ("c", "s", "q", "t"):
            # 相對指令的所有控制點與終點都是「相對指令起點」，不是逐點累加
            base_x, base_y = x, y
            for j in range(0, need, 2):
                px, py = args[j], args[j + 1]
                ax = base_x + px if rel else px
                ay = base_y + py if rel else py
                pts.append((ax, ay))
            x, y = ax, ay
        elif low == "a":
            ex, ey = args[5], args[6]
            x = x + ex if rel else ex
            y = y + ey if rel else ey
            pts.append((x, y))
    return pts

FORBIDDEN = {
    "image": "點陣圖放大會糊、縮小會髒，而且不能用 currentColor 換色",
    "text": "依賴字型，面板上不一定有；請用線條畫出來",
    "filter": "特效在不同底色下表現不一致，線條會顯髒",
    "foreignobject": "本質是 HTML 疊圖，匯出與相容性都會出問題",
}


def check(path: Path) -> list[tuple[str, str, str]]:
    """回傳 [(level, code, message)]，level ∈ error / warning。"""
    issues: list[tuple[str, str, str]] = []

    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        issues.append(("warning", "W7", "檔案有 UTF-8 BOM，部分渲染器會多出怪字元"))
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return [("error", "E0", "不是 UTF-8 編碼")]

    # ---- 檔名 ----
    if not NAME_RE.match(path.name):
        issues.append(("error", "E1", f"檔名不符 <domain>-<name>.svg（可用前綴：{' / '.join(DOMAINS)}）"))

    # ---- 根元素 ----
    head_m = re.search(r"<svg\b[^>]*>", text, re.I | re.S)
    if not head_m:
        return issues + [("error", "E2", "找不到 <svg> 根元素")]
    head = head_m.group(0).replace("'", '"')

    if 'viewBox="0 0 24 24"' not in head:
        issues.append(("error", "E2", '根元素必須是 viewBox="0 0 24 24"'))
    if 'fill="none"' not in head:
        issues.append(("error", "E3", '根元素需要 fill="none"（大面積填色在深色底會變亮塊）'))
    if "currentColor" not in head:
        issues.append(("error", "E3", '根元素需要 stroke="currentColor"，否則無法用 CSS 換狀態色'))
    if "xmlns" not in head:
        issues.append(("warning", "W7", "根元素缺少 xmlns，用 <img> 載入時可能不顯示"))
    if re.search(r"(?<![\w-])width\s*=", head) or re.search(r"(?<![\w-])height\s*=", head):
        issues.append(("warning", "W5", "根元素寫了 width/height，會蓋掉 CSS 縮放（只留 viewBox 就好）"))

    sw_m = re.search(r'stroke-width\s*=\s*"([^"]+)"', head)
    if not sw_m:
        issues.append(("warning", "W2", "根元素沒有 stroke-width，建議統一設 2"))
    else:
        try:
            sw = float(sw_m.group(1))
            if sw not in ALLOWED_STROKES:
                issues.append(("warning", "W2", f"stroke-width={sw} 不在建議值 {ALLOWED_STROKES}"))
        except ValueError:
            issues.append(("warning", "W2", "stroke-width 不是數字"))

    for key in ("stroke-linecap", "stroke-linejoin"):
        if f'{key}="round"' not in head:
            issues.append(("warning", "W3", f'根元素建議加 {key}="round"'))

    # ---- 寫死的顏色 ----
    stripped = re.sub(r"url\(\s*#[^)]*\)", "", text)                    # url(#gradient) 不是顏色
    stripped = re.sub(r"var\(\s*--icon-accent\s*(?:,[^)]*)?\)", "", stripped)
    stripped = re.sub(r"currentColor", "", stripped, flags=re.I)
    stripped = re.sub(r"\bnone\b", "", stripped, flags=re.I)
    if HEX_RE.search(stripped) or FUNC_RE.search(stripped):
        issues.append(("error", "E4", "出現寫死的顏色（#hex / rgb() / hsl()），請改用 currentColor"))

    # ---- 禁用元素 ----
    for tag, why in FORBIDDEN.items():
        if re.search(r"<" + tag + r"\b", text, re.I):
            issues.append(("error", "E5", f"<{tag}>：{why}"))
    if re.search(r"<style\b", text, re.I) or re.search(r'\sstyle\s*=', text, re.I):
        issues.append(("warning", "W6", "出現 <style> 或 style=\"…\"，會和外部主題打架"))
    if re.search(r"<(linear|radial)Gradient\b", text, re.I):
        issues.append(("warning", "W7", "出現漸層，深色或淺色底一定有一邊難看；圖示請用純線條"))

    # ---- 點綴色機制 ----
    if re.search(r'class\s*=\s*"[^"]*\baccent\b', text) and "var(--icon-accent" not in text:
        issues.append(("warning", "W4", 'class="accent" 的元素請用 stroke="var(--icon-accent, currentColor)"'))

    # ---- 幾何範圍 ----
    errors, warns = [], []

    def scan(attr: str, numbers: list[float], safe_area: bool) -> None:
        for n in numbers:
            if n < -0.5 or n > 24.5:
                errors.append(f"{attr} 出現 {n:g}，超出 0..24 畫布")
            elif safe_area and (n < 2 or n > 22):      # 安全區與 style-guide.md 一致：2～22
                warns.append(f"{attr} 出現 {n:g}，超出 2..22 安全區")

    for attr, val in ATTR_RE.findall(text):
        if attr == "d":
            scan(attr, [v for pt in path_points(val) for v in pt], safe_area=True)
        elif attr == "points":
            scan(attr, [float(x) for x in NUM_RE.findall(val)], safe_area=True)
        else:
            scan(attr, [float(x) for x in NUM_RE.findall(val)], safe_area=attr not in SIZE_ATTRS)

    for msg in list(dict.fromkeys(errors))[:4]:
        issues.append(("error", "E6", msg))
    for msg in list(dict.fromkeys(warns))[:4]:
        issues.append(("warning", "W1", msg))

    return issues


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="智慧建築圖示規格檢查")
    ap.add_argument("paths", nargs="+", help="SVG 檔或資料夾（可多個）")
    ap.add_argument("--json", action="store_true", help="以 JSON 輸出（給腳本用）")
    ap.add_argument("--strict", action="store_true", help="warning 也算失敗（CI 用）")
    args = ap.parse_args()

    files: list[Path] = []
    for p in args.paths:
        path = Path(p)
        files.extend(sorted(path.rglob("*.svg")) if path.is_dir() else [path])
    if not files:
        print("找不到任何 .svg 檔")
        return 2

    report, n_err, n_warn = [], 0, 0
    for f in files:
        issues = check(f)
        errs = [i for i in issues if i[0] == "error"]
        warns = [i for i in issues if i[0] == "warning"]
        n_err += len(errs)
        n_warn += len(warns)
        report.append({"file": str(f), "errors": errs, "warnings": warns})
        if not args.json:
            if not issues:
                print(f"  OK   {f.name}")
            else:
                print(f"  --   {f.name}")
                for level, code, msg in issues:
                    mark = "x" if level == "error" else "!"
                    print(f"        [{mark}] {code} {msg}")

    if args.json:
        print(json.dumps({"files": report, "errors": n_err, "warnings": n_warn}, ensure_ascii=False, indent=2))
    else:
        print(f"\n檢查 {len(files)} 個檔案：{n_err} error / {n_warn} warning")

    return 1 if (n_err or (args.strict and n_warn)) else 0


if __name__ == "__main__":
    sys.exit(main())
