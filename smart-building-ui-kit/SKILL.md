---
name: smart-building-ui-kit
description: 為智慧建築中控系統（圖控／HMI／觸控面板／Web 管理台／App）設計並產出 UI 圖示（SVG 向量圖示集）與背景圖（PNG 大圖）。當使用者提到「圖示、icon、圖標、SVG、設備圖、中控台要用的圖、幫我畫一個門禁／對講機／電梯／攝影機的圖、圖控介面圖案、圖示集、icon set、把圖示匯出成 PNG」或「背景圖、主視覺、banner、樓層平面底圖、開屏圖、簡報封面、中控大屏底圖」時，即使對方沒說「一整套」或沒說「智慧建築」，只要場景落在建築自動化／社區對講／門禁／機電監控／能源管理，就應該使用這個 skill。也適用於既有圖示集的增補、一致性檢查（lint）與多尺寸匯出。關鍵詞：智慧建築、中控、圖控、HMI、對講機、門禁、讀卡機、圖示、SVG、背景圖、eunicom、寶麒。
compatibility: 需要 Python 3.10+ 執行規格檢查與匯出腳本（純標準庫，不需安裝套件）。PNG 匯出會自動挑算圖引擎：本機有 Chrome／Edge 就直接用、有 resvg 就用 resvg、Linux／mac 可用 `uv run --with cairosvg`——所以換機器不會因為缺函式庫就卡住。
---

# 智慧建築中控系統：圖示與背景圖工具包

## 這個 skill 產出什麼

1. **UI 圖示（SVG）** — 中控台、觸控面板、Web 管理台、App 上的設備與系統圖標。24×24 母版、線條風、顏色交給 CSS（`currentColor`），所以同一顆圖示能直接變成「運轉中／警報／離線」各種狀態色。
2. **背景圖（PNG）** — 中控台主視覺、樓層平面底圖、簡報封面、App 開屏。走繪圖模型產大圖（`generate_image`），或需要精準時用 SVG 幾何自己合成再匯出。

兩件事的規格完全不同（一個要求像素級一致、一個要求氛圍），所以下面的流程把它們分開處理。

## 三個鐵則

先讀完再動手，這三條決定了產出的東西能不能真的被工程師用：

1. **圖示用畫的，不用生成的。** 手寫 SVG，不要叫繪圖模型生 icon：模型生的 PNG 尺寸不一、線寬不一、換不了色、在 24px 會糊，而中控介面最需要的就是這四件事。圖示只有一個例外才動用模型——客戶要「有材質感的大圖示」時，那時它其實是插圖不是 icon。
2. **顏色不是圖示的事，是 UI 的事。** 圖示只描繪「這是什麼設備」，不描繪「它現在好不好」。狀態一律由 CSS 變數上色。理由：同一顆攝影機圖示要在十幾個狀態與深淺色面板上重複使用，寫死顏色等於要維護十幾個版本。
3. **一個 24×24 母版，其他尺寸都是匯出來的。** 不要為 64px 另畫一套「細節版」——那只會讓兩套很快就不一致。若某個概念在 24px 讀不出來，該修的是**概念**（換更單純的造型），不是加解析度。唯一例外：真的需要密度的圖示，用 `-dense` 後綴另存（例如 `nav-floorplan-dense.svg`），母版仍是 24 格。

## 工作流程

### Step 0：先確認清單，不要自己猜

開工前把這件事講清楚（使用者可能已經給了，沒給就用預設值反問一句）：

- 要哪些圖示？（從 `references/icon-catalog.md` 挑，或照該檔的「衍生規則」造新名字）
- 深色或淺色面板為主？（多數中控是深色，預設深色）
- 有沒有品牌色要當強調色？（沒說就用 `#2AA9E0`）
- 要不要背景圖？哪一種用途、什麼尺寸？

預設值（使用者說「隨便」時用這組）：深色中控面板、強調色 `#2AA9E0`、輸出到 `<cwd>/smart-building-ui/`、PNG 匯出尺寸 24/48/64/128。

### Step 1：建目錄

```
smart-building-ui/
├── icons/            # SVG 母版（交件主檔）
├── tokens.css        # 色彩權杖（複製 assets/tokens.css）
├── dist/png/         # 匯出的 PNG
├── preview.html      # 人工驗收頁（腳本產生）
├── manifest.json     # 清單＋雜湊（腳本產生）
└── backgrounds/      # 背景圖 PNG ＋ prompts.md
```

`tokens.css` 複製自 `assets/tokens.css`，不要重寫一份——那會讓旗標色到處不一致。

### Step 2：寫圖示

從 `assets/icon-template.svg` 起手，造型參考 `assets/examples/` 裡那六顆（對講機、半球攝影機、讀卡機、空調、電表、平面圖）——它們就是尺規，新圖示的線條密度、圓角、留白要和它們一致。

造型邏輯寫在 `references/icon-catalog.md`：每顆圖示列了「必畫元素」與「避免」，照著畫就能在 24px 讀得出來。

### Step 3：自我檢查（一定要跑）

```bash
python scripts/svg_lint.py icons/
```

lint 會抓：檔名不符、viewBox 不對、寫死顏色、用了 `<image>`／`<text>`／`<filter>`、幾何超出畫布。有 error 就修到全綠；warning 逐條判斷，合理就留。

### Step 4：出驗收頁給人看

```bash
python scripts/preview_sheet.py icons/ -o . --tokens tokens.css
```

產生 `preview.html`（同一顆圖示並排：淺色底、深色底、五種狀態色、四種尺寸）＋ `manifest.json`。**圖示這種東西一定要讓人用眼睛驗收**——lint 綠不代表看起來對。把 `preview.html` 的路徑給使用者，請他看完再往下走。

### Step 5：匯出 PNG

```bash
python scripts/export_png.py icons/ -o dist/png --sizes 24,48,64,128,512 --ink "#E6EDF5"
```

腳本會把 `currentColor` 與 `var(--icon-accent, …)` 換成實際顏色再算圖，所以 PNG 和 `preview.html` 看到的完全一致（它預設就用同一顆瀏覽器引擎）。深淺兩套要各匯一次（`--ink` 不同、輸出目錄不同）。需要不透明的底圖（例如要貼進不支援透明的系統）加 `--bg "#0A111B"`。

**算圖引擎會自動挑**：本機 Chrome／Edge → resvg → cairosvg → svglib。Windows 上 cairo 函式庫常常不存在，所以不要寫死 `cairosvg`——真的需要排查時用 `--renderer chrome` 指定。匯出完抽查一張 PNG 開起來看，不要只看腳本沒報錯。

### Step 6：背景圖（只有被要求時才做）

讀 `references/background-recipes.md`，那裡有四種用途的現成 prompt、共用色票描述句、以及「模型畫不好就退回 SVG 合成」的判斷點。每次生成都把完整 prompt 寫進 `backgrounds/prompts.md`（含日期與尺寸），不然下次要重現一模一樣的圖就沒救了。

生成完還有**兩件一定要做的事**（實測踩到的）：

1. **歸檔**：Cherry Studio 生成的圖會落在 `%APPDATA%\CherryStudio\Data\Files\<uuid>.jpg`，要複製進 `backgrounds/` 並改成看得懂的名字。
2. **修尺寸**：模型不一定照 prompt 的比例走（要 16:9 它可能給你 1:1），而且右下角通常有「AI生成」浮水印。用 `scripts/fit_image.py` 一次解決：

```bash
python scripts/fit_image.py backgrounds/hero-01.jpg \
    -o backgrounds/hero-1920x1080.png --size 1920x1080 --zoom 1.04 --position center
```

裁完**一定要開起來看**：浮水印切乾淨了嗎？主體有沒有被切到？留白區還在不在？

### Step 7：交件報告

回報四件事：圖示清單（檔名＋一句話用途）、`preview.html` 路徑、PNG 匯出目錄與尺寸、背景圖 prompt 檔路徑。不要把 SVG 原始碼貼一大串在對話裡——使用者要的是檔案。

## 圖示規格（不可妥協項）

| 項目 | 規格 | 為什麼 |
|---|---|---|
| 畫布 | `viewBox="0 0 24 24"`，不寫 `width`/`height` | 寫死尺寸會蓋掉 CSS 縮放，24 以外的尺寸就爆了 |
| 安全區 | 內容落在 2～22 之間（等於留 2px 邊距） | 中控卡片上的圖示通常有底色塊，貼邊會黏在一起 |
| 線寬 | `stroke-width="2"`，全部同一條 | 混線寬是最常見的「看起來很業餘」原因 |
| 線端／接角 | `stroke-linecap="round"`、`stroke-linejoin="round"` | 尖角在深色底會有視覺雜點 |
| 顏色 | 根元素 `stroke="currentColor"`、`fill="none"`；**不得出現 `#hex`／`rgb()`** | `currentColor` 才能靠 CSS 換成狀態色 |
| 點綴色 | 標 `class="accent"` 的元素用 `stroke="var(--icon-accent, currentColor)"` | 容許雙色調，但沒給變數時自動退回單色 |
| 禁用元素 | `<image>`、`<text>`、`<filter>`、`<foreignObject>`、`<style>` | 點陣會糊、文字依賴字型、特效會髒；`<style>` 會和外部主題打架 |
| 命名 | `<domain>-<name>.svg`，小寫 kebab-case | 見下表 |
| 圓角 | 方框類用 `rx="2"`（小板件 1.5～2.5） | 統一圓角讓一整排圖示看起來是同一家人 |
| 對齊 | 座標盡量落在 0.5 或整數格 | 奇數座標 + 線寬 2 會造成邊緣模糊 |

**domain 前綴**（決定這顆圖示住在哪一區，也讓 lint 能驗檔名）：

| 前綴 | 範圍 | 例子 |
|---|---|---|
| `dev-` | 設備本體 | `dev-intercom`、`dev-camera-dome`、`dev-elevator` |
| `sec-` | 安防／對講 | `sec-access-card`、`sec-visitor`、`sec-sos` |
| `mep-` | 機電（空調、給排水、消防、照明） | `mep-hvac`、`mep-water-pump`、`mep-fire` |
| `nrg-` | 能源與計量 | `nrg-meter`、`nrg-solar`、`nrg-demand` |
| `sens-` | 感測器 | `sens-temperature`、`sens-air-quality`、`sens-co2` |
| `ctrl-` | 操作／控制 | `ctrl-power`、`ctrl-auto`、`ctrl-schedule` |
| `nav-` | 導覽／空間／架構 | `nav-floorplan`、`nav-building`、`nav-room` |
| `sts-` | 狀態圖例（只用在圖例與報表） | `sts-online`、`sts-alarm`、`sts-offline` |

## 狀態色怎麼用

`tokens.css` 定義五個狀態色：`--state-online`（運轉中）、`--state-active`（選取中）、`--state-warning`、`--state-alarm`、`--state-offline`。用法：

```html
<span class="icon" style="color: var(--state-alarm)"><svg …>…</svg></span>
```

深色面板用 `[data-theme="dark"]` 覆寫 `--icon-ink`，圖示檔案一行都不用改。

**什麼時候才需要 `sts-` 圖示**：圖例、報表、下拉選單這類沒有顏色語意的地方。設備卡片上的狀態請用顏色，不要換圖示——否則使用者得學兩套語彙。

**要狀態點的話**：不要每顆圖示各畫各的點，用固定幾何（右上角 `cx=19 cy=5 r=3`，外圈 2px 底色挖空）在 UI 層疊上去，這樣一排列的點才會在同一條線上。

## 遇到複雜圖案時

24px 塞不下細節是常態，處理順序是：**砍元素 → 改造型 → 才考慮 `-dense` 變體**。判斷方法：把圖示縮到 24px 後閉上一隻眼瞇著看，還認得出是什麼，就過關；要靠細節才認得出來，就得換一個更能代表它的輪廓（例如「配電盤」不要畫內部接線，畫一個箱子加一道閃電）。詳見 `references/style-guide.md` 的「簡化決策」。畫完記得跑 Step 3 的 lint 與 Step 4 的驗收頁。

## 背景圖的邊界

繪圖模型對「氛圍」很在行，對「精確」很不在行。所以：

- **很適合**：主視覺、氛圍底圖、封面、開屏。
- **不適合**：樓層平面圖（模型會畫出假房間與假標註）、需要真實比例的設備外觀圖。
- 需要精確的場合，退回 SVG：用幾何＋色塊自己合成 `backgrounds/*.svg`，再用 `export_png.py` 算成 PNG。這條路徑可重現、可微調，而且不會出現幻覺文字。

## 參考檔案與腳本

| 檔案 | 什麼時候讀 |
|---|---|
| `references/style-guide.md` | 開工前讀一次。完整設計規範：格線、顏色、狀態、簡化決策、常見錯誤對照 |
| `references/icon-catalog.md` | 挑圖示清單時。四十幾顆常用圖示的必畫元素／避免事項，以及新圖示的衍生規則 |
| `references/background-recipes.md` | 要做背景圖時。四種用途的 prompt、共用色票描述句、檢查清單 |
| `assets/icon-template.svg` | 起手模板 |
| `assets/tokens.css` | 複製進專案的色彩權杖 |
| `assets/examples/*.svg` | 造型尺規（六顆範例） |
| `scripts/svg_lint.py` | Step 3 規格檢查 |
| `scripts/preview_sheet.py` | Step 4 驗收頁＋manifest |
| `scripts/export_png.py` | Step 5 PNG 匯出（含 `--ink` 主題色、`--bg` 底色、自動挑引擎） |
| `scripts/fit_image.py` | Step 6 生成圖修尺寸（cover 裁切、去浮水印） |

## 交件前的自我檢查清單

- [ ] `svglint` 全綠（error 0）
- [ ] 所有圖示用同一條線寬、同一組圓角，排在一起像同一套
- [ ] 縮到 24px 還認得出來是什麼設備
- [ ] 檔名全部符合 `<domain>-<name>.svg`，沒有中文檔名
- [ ] `preview.html` 已產生，且真的開起來看過（不是只看腳本沒報錯）
- [ ] 有寫死顏色的圖示已清掉（換狀態色才不會失效）
- [ ] 若有背景圖：`backgrounds/prompts.md` 記了完整 prompt、尺寸、日期
- [ ] 背景圖已用 `fit_image.py` 修成目標比例，且確認浮水印已被裁掉
- [ ] 有匯出 PNG 的話，至少隨機開一張起來看過（不是只看腳本 exit code）
- [ ] 交件訊息裡有檔案路徑，而不是把整份 SVG 貼在對話中
