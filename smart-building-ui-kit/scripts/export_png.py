#!/usr/bin/env python3
"""export_png.py — 把 SVG 算成 PNG（圖示與背景圖都可以）

用法：
    # 圖示：一套多尺寸（會自動挑可用的算圖引擎）
    python export_png.py icons/ -o dist/png --sizes 24,48,64,128,512

    # 深色面板版本（只換線條色，來源檔案不用動）
    python export_png.py icons/ -o dist/png-dark --sizes 24,48,64 --ink "#E6EDF5"

    # 帶底色（做預覽圖或給不支援透明的系統用）
    python export_png.py icons/ -o dist/png --bg "#0A111B"

    # 背景圖：只給一個寬度，高度依原始比例自動換算
    python export_png.py backgrounds/floor.svg -o dist --sizes 1920

    # 指定引擎（出問題時排查用）
    python export_png.py icons/ -o dist --renderer chrome

為什麼要這支腳本：SVG 裡的 currentColor 與 var(--icon-accent) 是給瀏覽器用的，
算圖引擎不一定認得。這裡先把它們換成實際顏色再算，PNG 才會和網頁上看到的長得一樣。
另外它會依序嘗試多種引擎——因為 Windows 上 cairo 函式庫常常缺席，
硬要依賴單一引擎的話，換一台機器就跑不動。
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ACCENT_RE = re.compile(r"var\(\s*--icon-accent\s*(?:,\s*([^)]*?)\s*)?\)")
VIEWBOX_RE = re.compile(r'viewBox\s*=\s*"\s*([-\d.]+)[\s,]+([-\d.]+)[\s,]+([-\d.]+)[\s,]+([-\d.]+)\s*"')

CHROME_CANDIDATES = (
    os.environ.get("CHROME_PATH", ""),
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
)


def resolve_colors(svg: str, ink: str, accent: str) -> str:
    """把 CSS 變數與 currentColor 換成實際色碼（算圖引擎不認得這兩種寫法）。"""
    svg = re.sub(r"<\?xml.*?\?>|<!DOCTYPE.*?>", "", svg, flags=re.S)

    def repl(m: "re.Match[str]") -> str:
        fallback = (m.group(1) or "").strip().strip("'\"")
        return accent or fallback or ink

    return ACCENT_RE.sub(repl, svg).replace("currentColor", ink)


def aspect(svg: str) -> tuple[float, float]:
    m = VIEWBOX_RE.search(svg)
    if not m:
        return (1.0, 1.0)
    _, _, w, h = (float(x) for x in m.groups())
    return (w or 1.0, h or 1.0)


def parse_sizes(raw: str) -> list[int]:
    return [int(x) for x in re.split(r"[,\s]+", raw.strip()) if x]


# --------------------------------------------------------------------------- 引擎

class Backend:
    name = "?"
    note = ""

    def available(self) -> bool:
        return False

    def render(self, svg: str, out: Path, width: int, height: int, ink: str, accent: str, bg: str) -> None:
        raise NotImplementedError


def find_browser() -> str:
    """找出本機的 Chrome／Edge（有就用，不必安裝任何東西）。"""
    for cand in CHROME_CANDIDATES:
        if cand and Path(cand).exists():
            return cand
    for name in ("chrome", "google-chrome", "chromium", "chromium-browser", "msedge", "edge"):
        found = shutil.which(name)
        if found:
            return found
    return ""


def screenshot_html(
    html: str, out: Path, width: int, height: int, exe: str,
    profile_dir: str | Path, bgcolor: str = "00000000",
) -> None:
    """把一段 HTML 用 headless 瀏覽器截成圖片（尺寸就是視窗尺寸）。

    為什麼走瀏覽器：Windows 上 cairo 函式庫常常不存在，而 resvg 要另外裝。
    瀏覽器幾乎每台機器都有，而且它算出來的結果和設計師在預覽頁看到的完全一致。
    """
    tmp = Path(tempfile.mkdtemp(prefix="svgshot-"))
    page = tmp / "page.html"
    page.write_text(html, encoding="utf-8")
    if out.exists():
        out.unlink()
    cmd = [
        exe, "--headless=new", "--disable-gpu", "--hide-scrollbars",
        "--no-first-run", "--no-default-browser-check", "--force-device-scale-factor=1",
        f"--user-data-dir={profile_dir}",
        f"--window-size={width},{height}",
        f"--default-background-color={bgcolor}",
        f"--screenshot={out}",
        page.as_uri(),
    ]
    subprocess.run(cmd, capture_output=True, timeout=180)
    for _ in range(80):                     # 等瀏覽器把檔案寫完
        if out.exists() and out.stat().st_size > 0:
            return
        time.sleep(0.25)
    raise RuntimeError("headless 瀏覽器沒有產出檔案")


class ChromeBackend(Backend):
    name = "chrome (headless 瀏覽器，與 preview.html 完全同一顆引擎)"

    def __init__(self) -> None:
        self.exe = find_browser()
        self.tmp = Path(tempfile.mkdtemp(prefix="svg2png-"))

    def available(self) -> bool:
        return bool(self.exe)

    def render(self, svg: str, out: Path, width: int, height: int, ink: str, accent: str, bg: str) -> None:
        bgcolor = (bg.lstrip("#") + "FF") if bg else "00000000"
        screenshot_html(
            "<!DOCTYPE html><html><head><meta charset=\"utf-8\"><style>"
            "html,body{margin:0;padding:0;background:transparent}"
            f".icon{{width:{width}px;height:{height}px;color:{ink};--icon-accent:{accent or ink}}}"
            ".icon svg{width:100%;height:100%;display:block}"
            "</style></head><body>"
            f'<div class="icon">{svg}</div></body></html>',
            out, width, height, self.exe, self.tmp / "profile", bgcolor,
        )


class ResvgBackend(Backend):
    name = "resvg (Rust 靜態二進位，最快也最準)"

    def available(self) -> bool:
        return bool(shutil.which("resvg"))

    def render(self, svg: str, out: Path, width: int, height: int, ink: str, accent: str, bg: str) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "in.svg"
            src.write_text(svg, encoding="utf-8")
            cmd = ["resvg", "--width", str(width), "--height", str(height)]
            if bg:
                cmd += ["--background", bg]
            cmd += [str(src), str(out)]
            subprocess.run(cmd, check=True, capture_output=True, timeout=120)


class CairoSvgBackend(Backend):
    name = "cairosvg (Linux／mac 常見；Windows 需要 cairo DLL)"

    def available(self) -> bool:
        try:
            import cairosvg  # noqa: F401
        except Exception:
            return False
        return True

    def render(self, svg: str, out: Path, width: int, height: int, ink: str, accent: str, bg: str) -> None:
        import cairosvg  # type: ignore

        cairosvg.svg2png(
            bytestring=svg.encode("utf-8"), write_to=str(out),
            output_width=width, output_height=height, background_color=bg or None,
        )


class SvglibBackend(Backend):
    name = "svglib + reportlab（純 Python 後備方案）"

    def available(self) -> bool:
        try:
            import rlPyCairo  # noqa: F401
            import reportlab  # noqa: F401
            import svglib  # noqa: F401
        except Exception:
            return False
        return True

    def render(self, svg: str, out: Path, width: int, height: int, ink: str, accent: str, bg: str) -> None:
        import io

        from reportlab.graphics import renderPM
        from svglib.svglib import svg2rlg

        drawing = svg2rlg(io.StringIO(svg))
        scale = width / max(drawing.width, 1.0)
        drawing.scale(scale, scale)
        renderPM.drawToFile(drawing, str(out), fmt="PNG", dpi=72, bg=bg or 0xFFFFFF)


def pick_backend(preferred: str) -> Backend:
    order: list[Backend] = [ChromeBackend(), ResvgBackend(), CairoSvgBackend(), SvglibBackend()]
    if preferred != "auto":
        for b in order:
            if b.name.split(" ")[0].lower() == preferred:
                if b.available():
                    return b
                print(f"指定的引擎 {preferred} 不可用，改用自動挑選。")
                break
    for b in order:
        if b.available():
            return b
    raise SystemExit(
        "找不到可用的 SVG 算圖引擎。任選一種即可：\n"
        "  1. 安裝 Chrome 或 Edge（本機已有瀏覽器就能用，免安裝其他東西）\n"
        "  2. mise 安裝 resvg：mise use -g aqua:linebender/resvg\n"
        "  3. uv run --with cairosvg python export_png.py …（Linux／mac）\n"
        "  4. uv run --with svglib --with reportlab --with pycairo --with rlPyCairo python export_png.py …\n"
    )


# --------------------------------------------------------------------------- 主程式

def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    ap = argparse.ArgumentParser(description="SVG → PNG（多尺寸、主題色、自動挑引擎）")
    ap.add_argument("src", help="SVG 檔或資料夾")
    ap.add_argument("-o", "--out", required=True, help="輸出資料夾")
    ap.add_argument("--sizes", default="24,48,64,128,512", help="尺寸（寬），逗號分隔；非正方形會自動算高度")
    ap.add_argument("--ink", default="#1F2A37", help="主線條顏色（取代 currentColor），預設 #1F2A37")
    ap.add_argument("--accent", default="", help="點綴色（取代 var(--icon-accent)），預設沿用 SVG 內的 fallback")
    ap.add_argument("--bg", default="", help="背景色，例如 #0A111B；預設透明")
    ap.add_argument("--name-suffix", default="", help="檔名後綴，例如 -dark")
    ap.add_argument("--renderer", default="auto", choices=["auto", "chrome", "resvg", "cairosvg", "svglib"])
    args = ap.parse_args()

    src = Path(args.src)
    files = sorted(src.rglob("*.svg")) if src.is_dir() else [src]
    if not files:
        print(f"找不到任何 .svg 檔：{args.src}")
        return 2

    backend = pick_backend(args.renderer)
    print(f"引擎：{backend.name}\n")

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    sizes = parse_sizes(args.sizes)
    made = 0

    for f in files:
        svg = resolve_colors(f.read_text(encoding="utf-8"), args.ink, args.accent)
        vb_w, vb_h = aspect(svg)
        for size in sizes:
            height = size if abs(vb_w - vb_h) < 1e-6 else max(1, round(size * vb_h / vb_w))
            target = out_dir / f"{f.stem}{args.name_suffix}-{size}.png"
            try:
                backend.render(svg, target, size, height, args.ink, args.accent, args.bg)
            except Exception as exc:                       # noqa: BLE001
                print(f"  x  {target.name} 失敗：{exc}")
                continue
            made += 1
            print(f"  {target}  ({size}x{height})")

    print(f"\n完成：{len(files)} 個 SVG → {made} 個 PNG，輸出於 {out_dir}")
    return 0 if made else 1


if __name__ == "__main__":
    sys.exit(main())
