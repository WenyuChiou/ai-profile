<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/WenyuChiou/ai-profile/main/docs/assets/banner-dark.svg">
  <img alt="ai-profile－在保護隱私的前提下呈現你的 AI 協作" src="https://raw.githubusercontent.com/WenyuChiou/ai-profile/main/docs/assets/banner-light.svg" width="100%">
</picture>

# ai-profile

[![PyPI](https://img.shields.io/pypi/v/ai-profile-cli.svg)](https://pypi.org/project/ai-profile-cli/)
[![tests](https://github.com/WenyuChiou/ai-profile/actions/workflows/ci.yml/badge.svg)](https://github.com/WenyuChiou/ai-profile/actions/workflows/ci.yml)
[![license: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/WenyuChiou/ai-profile/blob/main/LICENSE)
[![python 3.11–3.14](https://img.shields.io/badge/python-3.11%E2%80%933.14-blue.svg)](https://github.com/WenyuChiou/ai-profile/blob/main/pyproject.toml)

[English](https://github.com/WenyuChiou/ai-profile/blob/main/README.md) · [繁體中文](https://github.com/WenyuChiou/ai-profile/blob/main/README.zh-TW.md)

呈現你如何與 AI 協作，而不只是你提交了多少 commit。`aiprofile`
把本機 Git 歷史中的明示 AI 參與證據，轉成可放在 GitHub Profile
README 的可信、隱私安全 SVG 卡片與自包含互動 dashboard。

如果你想建立有證據的 AI 作品形象，又不想上傳原始碼、根據程式風格
猜測 attribution，或暴露 repository 身分，就適合使用它。`aiprofile`
會辨識 `AI-*` commit trailer 與經驗證的 AI co-author 身分，跨
repository 彙整活動，並把資料庫保留在你的電腦上。

它不是 AI 程式碼偵測器。沒有明示證據的 commit 會維持為
`unknown`，不會被猜測為人類撰寫，也不會被推測成任何 provider。

- **可信：**所有 AI attribution 都來自明示的 Git 證據。
- **預設保護隱私：**repository 身分不會公開；每日日期只會在你明確選擇後
  顯示。
- **可直接展示：**一套本機流程即可產生亮色與深色的摘要、heatmap
  與 badge，並提供可依 provider 切換的互動 dashboard。

## 預覽

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/WenyuChiou/ai-profile/main/docs/assets/summary-sample-dark.svg">
  <img alt="以合成資料產生的 AI 協作摘要卡片" src="https://raw.githubusercontent.com/WenyuChiou/ai-profile/main/docs/assets/summary-sample-light.svg">
</picture>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/WenyuChiou/ai-profile/main/docs/assets/heatmap-sample-dark.svg">
  <img alt="AI 協作 heatmap：明暗代表總 commit 數，色相代表當日 AI 協作比例" src="https://raw.githubusercontent.com/WenyuChiou/ai-profile/main/docs/assets/heatmap-sample-light.svg">
</picture>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/WenyuChiou/ai-profile/main/docs/assets/badge-sample-dark.svg">
  <img alt="由 Git provenance 驗證的 AI 協作比例徽章" src="https://raw.githubusercontent.com/WenyuChiou/ai-profile/main/docs/assets/badge-sample-light.svg">
</picture>

以上範例皆使用合成資料。

## 安裝

需要 Python 3.11–3.14 與 Git 2.17 以上版本。支援 Windows、macOS
與 Linux。Git repository 必須使用 SHA-1 object format。

```bash
pip install ai-profile-cli
```

PyPI 套件名稱是 `ai-profile-cli`；安裝後的指令是 `aiprofile`。

## 快速開始

在其中一個 repository 的根目錄執行：

```bash
aiprofile init
aiprofile scan .
aiprofile aggregate
aiprofile render
```

- `init` 建立本機設定，並從 `git config user.email` 帶入你的身分。
- `scan` 記錄由已設定身分所建立的 commit。
- `aggregate` 顯示可以公開的完整隱私安全統計。
- `render` 在 `dist/` 產生六個 SVG 檔案、`dashboard.html` 與
  `profile.json`。

只有 `~/.aiprofile/config.json` 內身分所建立的 commit 會被計算。請檢查
`init` 帶入的 email，並加入其他曾用來 commit 的地址。

之後可以隨時掃描其他 repository：

```bash
aiprofile scan /path/to/another/repository
```

Repository 預設為 `aggregate_only`：數字會計入摘要，但 repository
身分與每日日期不會公開。`--full` 會把該 repository 的彙總活動明確標記
為可發布，讓其日期出現在日期型視圖。這是發布政策選擇，不代表該
repository 在 GitHub 上公開：

```bash
aiprofile scan --full /path/to/repository
```

這項選擇會持續保留；之後不用 `--full` 重新掃描，也不會自動降級。
若要停止發布日期，請在 `~/.aiprofile/config.json` 把該 repository 的
`publication_level` 改為 `aggregate_only`（保留隱去 repository 身分的
彙總數字）或 `excluded`（完全排除），再重新執行 `aggregate` 與
`render`。

同一個輸出目錄一次只能執行一個 `render`。

## 加到 GitHub Profile

在你的 GitHub Profile repository（`USERNAME/USERNAME`）中產生卡片，
接著 commit 產生的 `dist/` 目錄，並把以下內容加入 README：

```html
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="dist/summary-dark.svg">
  <img alt="AI collaboration summary" src="dist/summary-light.svg">
</picture>
```

`heatmap-{light,dark}.svg` 與 `badge-{light,dark}.svg` 也使用相同格式。
需要更新卡片時，重新執行 `scan` 與 `render`，再 commit 更新後的檔案。

## 互動 dashboard

`dist/dashboard.html`
是由與 SVG 卡片相同的已驗證 aggregate data
產生的自包含 dashboard。
直接用瀏覽器開啟後，可以：

- 在 **All AI** 與單一 provider 之間切換；
- 分別查看 provider-attributed commits、actor presences 與 active
  days，不混用統計單位；
- 查看可發布範圍內的每日 AI 協作紀錄；
- 切換亮色、深色
  與系統色彩主題。

這個檔案不載入外部 script、font、tracker 或 API。
它包含與 `profile.json` 相同的公開 aggregate fields，
因此發布任一檔案前，都應先檢查
`aiprofile aggregate`。

GitHub README 不會執行 JavaScript。
請繼續在 Profile README 放置 SVG，
再將卡片連到 GitHub Pages 或其他 static host
上的 `dashboard.html`。可參考
[實際 Profile 範例](https://wenyuchiou.github.io/WenyuChiou/dist/dashboard.html)。

## 宣告 AI 參與

已知的 AI co-author 身分會被自動辨識。其他工具或更完整的 attribution，
可以在 commit message 加入 `AI-*` trailer block：

```text
feat: add aggregation service

AI-Provider: Anthropic
AI-Model: Claude-Sonnet
AI-Tool: Claude-Code
AI-Role: implementation, documentation
AI-Mode: AI-Assisted
AI-Reviewed-By: Human
```

在同一個 commit 重複 `AI-Provider:`，即可宣告另一個 AI actor。因此，
一個 commit 可以同時是 1 個 unique AI-attributed commit 與多個 actor
presence。只有明確由人類單獨完成時，才使用 `AI-Mode: Human-Only`。

## 隱私

- Repository 資料不會被上傳。CLI 不會發出網路請求，也沒有 telemetry。
- 新 repository 預設為 `aggregate_only`。`scan --full` 是明確的發布
  決定；也可以在 `~/.aiprofile/config.json` 將 repository 設為
  `excluded`。
- 公開資產只包含彙整數字、公開 provider 名稱、證據統計與日期；不包含
  repository 名稱或路徑、organization 名稱、branch、commit SHA 或
  message、原始 trailer、email。
- `aiprofile aggregate` 就是發布預覽。Commit 產生的資產前請先檢查。
- Aggregate-only 是身分遮蔽，不是匿名。持續發布仍可能透露統計何時改變。
  詳見完整的[隱私模型](https://github.com/WenyuChiou/ai-profile/blob/main/docs/PRIVACY.md)。
- 不要公開或同步 `~/.aiprofile`；其中包含私人 repository 路徑、身分與
  本機 salt。

## 指標

- **AI-attributed commits** 是至少包含一個明示 AI actor presence 的
  unique commit。
- **Actor presences** 計算一個 commit 中不同 provider/tool 的參與；
  provider 總數因此可能高於 unique commit 總數。
- **Unknown** 永遠與 human 分開。
- 證據品質標示為
  `verified > declared > imported > inferred > unknown`。

## 說明與支援

執行 `aiprofile --help` 或 `aiprofile COMMAND --help` 查看指令選項。
Bug 與功能建議請使用
[GitHub Issues](https://github.com/WenyuChiou/ai-profile/issues)；
漏洞請依照[安全政策](https://github.com/WenyuChiou/ai-profile/blob/main/SECURITY.md)回報。

## 貢獻與授權

歡迎參與，請見
[CONTRIBUTING.md](https://github.com/WenyuChiou/ai-profile/blob/main/CONTRIBUTING.md)。
本專案採用
[MIT License](https://github.com/WenyuChiou/ai-profile/blob/main/LICENSE)。
