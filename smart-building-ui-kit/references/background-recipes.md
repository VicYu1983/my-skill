# 背景圖食譜：中控系統常用大圖

> 要做背景圖時讀這份。四種用途的現成 prompt、共用色票句、以及「什麼時候不該用模型」。

## 目錄

1. [通用規則](#1-通用規則)
2. [共用色票描述句](#2-共用色票描述句)
3. [生成之後：比例、浮水印、歸檔](#3-生成之後比例浮水印歸檔)
4. [食譜 A：中控台主視覺](#食譜-a中控台主視覺-1920×1080)
5. [食譜 B：樓層平面底圖](#食譜-b樓層平面底圖用-svg-合成不要用模型)
6. [食譜 C：簡報／型錄封面](#食譜-c簡報型錄封面-1920×1080)
7. [食譜 D：App 開屏](#食譜-dapp-開屏-1080×1920)
8. [生成後檢查清單](#7-生成後檢查清單)
9. [記錄格式](#8-記錄格式)

---

## 1. 通用規則

背景圖跟圖示是兩種完全不同的工作。圖示要求像素級一致，背景圖要求氛圍；所以這裡的規則也完全不同：

- **一律用英文寫 prompt。** 繪圖模型對英文的構圖與風格詞理解最穩，中文常導致主體漂移。
- **色碼直接寫進 prompt。** 寫 `deep navy background (#0A111B)` 比寫「深藍色背景」準得多。
- **每張都要加這段尾巴**：`no text, no letters, no numbers, no watermark, no logo, no signature`。模型一定會想塞假文字，而中控大圖上一旦出現亂碼字，那張圖就廢了。
- **明講留白。** UI 要疊標題、KPI 卡、按鈕的地方必須是空的，否則圖再美也不能用。用 `left third mostly empty dark space`、`generous negative space at the top` 這種描述。
- **一次生 2～4 張候選**，挑一張，其餘刪掉。不要只生一張就用，也不要生十張挑不出來。
- **同一批圖共用同一段色票描述句**，只換主體。這樣整組放在一起才像同一套設計。

## 2. 共用色票描述句

每次複製這段，接在主體描述後面：

```
, deep navy background (#0A111B to #12283F gradient), cyan accent (#2AA9E0) glowing hairlines,
teal green (#30A46C) secondary highlights, matte dark glass panels with subtle bevels,
soft volumetric haze, cinematic lighting, ultra clean, high detail,
no text, no letters, no numbers, no watermark, no logo
```

## 3. 生成之後：比例、浮水印、歸檔

這三件事在 prompt 裡寫再多都沒用，只能生成後處理——以下是實測結果：

| 現象 | 實際情況 | 處理方式 |
|---|---|---|
| 比例 | prompt 寫 `16:9 aspect ratio`，模型還是可能給你 1:1（取決於繪圖模型設定） | 一律用 `scripts/fit_image.py` 裁成目標比例 |
| 浮水印 | 生成圖右下角會多一個「AI生成」標記 | 同上一支腳本：`--zoom 1.04`～`1.12` 把邊緣切掉 |
| 檔案位置 | Cherry Studio 把生成結果放在 `%APPDATA%\CherryStudio\Data\Files\<uuid>.jpg` | 複製進專案的 `backgrounds/`，改成看得懂的名字 |

```bash
# 去浮水印 + 轉 16:9（主體居中用 center；主體靠某一角就用 '0% 0%' 之類留住那一角）
python scripts/fit_image.py backgrounds/hero-01.jpg \
    -o backgrounds/hero-1920x1080.png --size 1920x1080 --zoom 1.04 --position center
```

**cover 裁切一定會切掉東西**，所以要挑一張「切掉邊緣也好看」的候選：主體不要貼邊、重要細節不要放在四角。這也是為什麼食譜裡的 prompt 一直強調留白——留白區被切掉不會痛，主體被切掉要重生。

裁完一定要開起來看：浮水印切乾淨了嗎？主體有沒有被切到？留白區還夠放標題嗎？

## 食譜 A：中控台主視覺（1920×1080）

**用途**：中控系統首頁橫幅、大屏待機畫面、產品頁首圖。
**構圖**：主體放右 2/3，左 1/3 留乾淨暗區給標題與 KPI 卡。

```
Futuristic smart building control room hero image, low angle view of a modern curved control
console with glowing holographic floor plan projections floating above it, faint silhouettes of
residential towers seen through a dark glass wall, subject placed on the right two thirds, left
third mostly empty dark space
+ 共用色票描述句
+ , 16:9 aspect ratio
```

## 食譜 B：樓層平面底圖（用 SVG 合成，不要用模型）

**為什麼不用模型**：模型畫不出可用的平面圖——它會生成看起來像平面圖但房間不閉合、動線穿牆、還帶假標註的圖。這種圖疊上真實設備點位後會誤導值班人員，比沒有底圖更糟。

改用 SVG 合成（可重現、可微調、可換色）：

```svg
<svg viewBox="0 0 1920 1080" xmlns="http://www.w3.org/2000/svg">
  <rect width="1920" height="1080" fill="#0A111B"/>
  <!-- 細格線 40px 週期 -->
  <pattern id="g" width="40" height="40" patternUnits="userSpaceOnUse">
    <path d="M40 0H0v40" fill="none" stroke="#22303F" stroke-width="1" opacity="0.55"/>
  </pattern>
  <rect width="1920" height="1080" fill="url(#g)"/>
  <!-- 主格線 200px 週期，再畫一層較亮的線（略） -->
  <!-- 房間色塊 -->
  <rect x="120" y="140" width="520" height="360" rx="6" fill="#141E2C" stroke="#22303F" stroke-width="2"/>
  <!-- 動線 -->
  <polyline points="160,900 640,900 640,520 1200,520 1200,860 1760,860"
            fill="none" stroke="#2AA9E0" stroke-width="3" stroke-dasharray="12 10" opacity="0.35"/>
  <!-- 暈影：邊緣壓暗，讓中間的設備點位更突出 -->
  <rect width="1920" height="1080" fill="url(#vignette)"/>
</svg>
```

合成後用 `scripts/export_png.py` 算成 PNG（那支腳本對任何 viewBox 都能算，不是只能處理圖示）。要淺色版就把 `#0A111B` / `#141E2C` / `#22303F` 換成 `#F7F9FC` / `#FFFFFF` / `#E6E6E6`。

## 食譜 C：簡報／型錄封面（1920×1080）

**用途**：提案簡報首頁、產品型錄封面、展場背板。
**構圖**：主體居中但不大，上下留大面積空白放標題與公司識別。

```
Minimal premium tech cover image: geometric abstract silhouette of a smart building formed by
thin glowing lines and translucent glass planes, faint exploded-view layers suggesting building
floors, centered composition with generous negative space above and below, subtle fine grid
texture
+ 共用色票描述句
+ , 16:9 aspect ratio
```

## 食譜 D：App 開屏（1080×1920）

**用途**：手機 App 啟動畫面、平板待機。
**構圖**：上 40% 留空放 logo，主體在中下段，底部散景不能干擾文字。

```
Vertical mobile splash background: a single modern building facade at night, thin glowing light
strips running along the facade edges, floating soft glowing particles, large empty dark area in
the upper 40 percent, gentle out of focus city lights in the bottom third
+ 共用色票描述句
+ , 9:16 vertical aspect ratio
```

## 7. 生成後檢查清單

看圖的時候逐項確認，任何一項不過就重生——背景圖重生的成本遠低於上線後被客戶發現：

- [ ] 沒有假文字、假數字、亂碼（最常見的失敗，放大到 100% 看角落）
- [ ] 沒有手、臉、人物怪異的細節（模型很愛偷塞）
- [ ] 指定的留白區真的是空的
- [ ] 主體沒有被切到邊，或切得剛好不自然
- [ ] 顏色對得上色票（拿 `#2AA9E0` 跟圖上的青色比一下，偏掉就重生或後製調色）
- [ ] 四張候選放在一起看，像同一套的嗎
- [ ] 若要跟其他背景圖並排，明暗與顆粒感一致嗎

## 8. 記錄格式

每張圖都要留 prompt，否則下次要生風格一致的圖就只能重猜。寫進 `backgrounds/prompts.md`：

```markdown
| 日期 | 檔名 | 尺寸 | 用途 | 完整 prompt |
|---|---|---|---|---|
| 2026-11-01 | hero-control-room-01.png | 1920×1080 | 中控台主視覺 | Futuristic smart building control room hero image, … |
```

同一個用途生了多版就用 `-01`、`-02` 編號，選中的那版在表格後面註記一行 `選用：hero-control-room-02.png（左側留白最乾淨）`。

原始生成檔（比例不對、有浮水印的那個）也要留著：日後要換尺寸時，從原始檔重裁比重新生成快得多，風格也不會跑掉。
