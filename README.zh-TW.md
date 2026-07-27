<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/WenyuChiou/ai-profile/main/docs/assets/banner-dark.svg">
  <img alt="" src="https://raw.githubusercontent.com/WenyuChiou/ai-profile/main/docs/assets/banner-light.svg" width="100%">
</picture>

# ai-profile

## 讓你的 AI 協作有證據可查。

`ai-profile` 會把本機多個 Git repository 中明確記錄的 provenance，
轉換成適合 GitHub Profile 的隱私安全卡片與可依 provider 篩選的 dashboard；
不需上傳原始碼，也不會猜測 attribution。

**[查看即時 dashboard →](https://wenyuchiou.github.io/WenyuChiou/dist/dashboard.html)**
· **[用四個指令產生你的 Profile](#快速開始)**

[![PyPI](https://img.shields.io/pypi/v/ai-profile-cli.svg)](https://pypi.org/project/ai-profile-cli/)
[![tests](https://github.com/WenyuChiou/ai-profile/actions/workflows/ci.yml/badge.svg)](https://github.com/WenyuChiou/ai-profile/actions/workflows/ci.yml)
[![license: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/WenyuChiou/ai-profile/blob/main/LICENSE)
[![python 3.11–3.14](https://img.shields.io/badge/python-3.11%E2%80%933.14-blue.svg)](https://github.com/WenyuChiou/ai-profile/blob/main/pyproject.toml)

[English](https://github.com/WenyuChiou/ai-profile/blob/main/README.md) ·
[繁體中文](https://github.com/WenyuChiou/ai-profile/blob/main/README.zh-TW.md)

- **明確證據：** attribution 來自 `AI-*` trailers 與已驗證的 AI
  co-author identities，不靠程式碼風格判斷。
- **本機優先的隱私：** scan、aggregate 與 render 都在你的電腦執行；
  repository identity 不會進入公開資產。
- **可直接放上 Profile：** 一次 render 會產生支援主題的 SVG 卡片、
  self-contained dashboard 與可供機器讀取的公開摘要。

`ai-profile` 不是 AI code detector。沒有證據的 commit 會維持
`unknown`（介面會顯示為**未歸屬**），不會被偷偷算成人類完成，也不會被指派給
任何 provider。若希望記錄未來 commit 的 AI 參與，請加入 `AI-*` trailers。

## 真實 GitHub Profile 範例

下方卡片使用維護者的真實公開 aggregate data。點擊即可開啟可依 provider
篩選的 dashboard。

<a href="https://wenyuchiou.github.io/WenyuChiou/dist/dashboard.html">
  <picture>
    <source media="(max-width: 600px) and (prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/WenyuChiou/WenyuChiou/main/dist/badge-dark.svg">
    <source media="(max-width: 600px)" srcset="https://raw.githubusercontent.com/WenyuChiou/WenyuChiou/main/dist/badge-light.svg">
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/WenyuChiou/WenyuChiou/main/dist/summary-dark.svg">
    <img alt="開啟 Wenyu Chiou 的互動式 AI 協作 dashboard" src="https://raw.githubusercontent.com/WenyuChiou/WenyuChiou/main/dist/summary-light.svg">
  </picture>
</a>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/WenyuChiou/WenyuChiou/main/dist/heatmap-dark.svg">
  <img alt="Wenyu Chiou 的 AI 協作 heatmap；深淺代表 commit 量，色相代表 AI 比例" src="https://raw.githubusercontent.com/WenyuChiou/WenyuChiou/main/dist/heatmap-light.svg">
</picture>

## 為什麼使用 ai-profile？

- 一般 GitHub 統計回答開發者**有多活躍**。
- line-level attribution 工具回答工具**改了哪些程式行**。
- `ai-profile` 回答**跨 repository 的 AI 如何參與，以及有哪些證據支持
  這項說法**，同時讓分析留在本機。

它是這些工具的補充，不是替代品；Git 中沒有證據時，它不會推測歷史 AI
使用情形。

## 安裝

需要 Python 3.11 以上與 Git 2.17 以上。wheel-onboarding workflow
會在 Ubuntu、Windows 與 macOS 的 Python 3.12 測試；完整測試也會在
Ubuntu 驗證 Python 3.11–3.14。Git repository 必須使用 SHA-1 object
format。

```bash
python -m pip install --upgrade ai-profile-cli
aiprofile --version
```

套件名稱是 `ai-profile-cli`，安裝後的指令是 `aiprofile`。若 shell 尚未
更新 scripts 路徑，請使用：

```bash
python -m aiprofile --version
```

## 快速開始

在任一 repository 根目錄執行：

```bash
aiprofile init
aiprofile scan .
aiprofile aggregate
aiprofile render
```

若有需要，所有指令都可用 `python -m aiprofile` 取代 `aiprofile`。

- `init` 建立本機設定，並從 `git config user.email` 帶入 identity。
- `scan` 讀取目前 `HEAD` 可到達的 commit，記錄由設定 identity
  author 的 commit。
- `aggregate` 顯示可公開的確切隱私安全統計。
- `render` 會在 `dist/` 寫入八個檔案：

```text
badge-dark.svg       heatmap-light.svg   summary-dark.svg
badge-light.svg      profile.json        summary-light.svg
dashboard.html       heatmap-dark.svg
```

既有 commit 若沒有明確 AI 證據，會顯示為 `unknown`。大量 unknown
是誠實結果，不代表 scan 失敗。若希望未來的 AI 參與被計入，請在新 commit
加入 trailers。

## 設定 identities 與 repository 隱私

設定檔位置：

- macOS/Linux：`~/.aiprofile/config.json`
- Windows：`%USERPROFILE%\.aiprofile\config.json`
  （PowerShell 為 `$HOME\.aiprofile\config.json`）
- 自動化自訂位置：`$AIPROFILE_HOME/config.json`

只有 author email 存在於 `identities` 的 commit 才會被計入。執行
`init` 後，先關閉其他 `aiprofile` 程序，再以 UTF-8 JSON 開啟設定檔，
加入所有使用的 email，包括 GitHub noreply address：

```json
{
  "identities": [
    "you@example.com",
    "12345678+username@users.noreply.github.com"
  ],
  "repositories": [],
  "salt": "保留既有的自動產生值"
}
```

請勿變更自動產生的 `salt`。完成 scan 後，每個 repository entry 也包含
`path`、`repository_uid` 與 `publication_level`。調整隱私時只修改
`publication_level`：

Windows 使用者請用編輯器的 **UTF-8（無 BOM）** 選項儲存。Windows
PowerShell 5.1 的 `Set-Content -Encoding utf8` 會加入 BOM；嚴格 JSON
reader（包含此 Public Beta）會拒絕該檔案。VS Code 預設的 `UTF-8`
編碼可用；取代備份前請先確認檔案仍能正確解析。

```json
{
  "path": "/由-scan-建立的本機路徑",
  "repository_uid": "保留既有的自動產生值",
  "publication_level": "aggregate_only"
}
```

可用值如下：

- `aggregate_only` — 預設值；納入總數，但不公開 repository identity
  與每日日期。
- `full` — 允許 identity-redacted 的每日 aggregate activity 進入日期視圖。
- `excluded` — 完全排除該 repository。

`aiprofile scan --full /path/to/repository` 是從 `aggregate_only`
選擇加入 `full` 的支援方式。它不代表該 repository 在 GitHub 是公開的，
之後不加 `--full` 的 scan 也不會自動降級。若要降低公開程度，只修改既有
entry 的 `publication_level`，以有效 UTF-8 JSON 儲存，然後執行：

```bash
aiprofile aggregate
aiprofile render
```

若設定檔解析失敗，請還原上一份有效 JSON；不要刪除或重建 `salt`、`path`
或 `repository_uid`。公開前一律先檢查 `aggregate`。

## Scan 與更新多個 repositories

逐一 scan repository，再彙整本機紀錄：

```bash
aiprofile scan /path/to/repository-one
aiprofile scan /path/to/repository-two
aiprofile aggregate
aiprofile render
```

Public Beta 尚無 batch refresh 指令。更新多 repository Profile 時，請對每個
歷史已變更的 repository 分別重跑 `scan`，再執行 `aggregate` 與
`render`。同一個輸出目錄一次只能執行一個 `render`。

## 發布到 GitHub Profile

在 `USERNAME/USERNAME` Profile repository 中執行
`aiprofile render --out dist`，commit `dist/`，並把這段可點擊卡片放入
README：

```html
<a href="https://USERNAME.github.io/USERNAME/dist/dashboard.html">
  <picture>
    <source media="(max-width: 600px) and (prefers-color-scheme: dark)" srcset="dist/badge-dark.svg">
    <source media="(max-width: 600px)" srcset="dist/badge-light.svg">
    <source media="(prefers-color-scheme: dark)" srcset="dist/summary-dark.svg">
    <img alt="開啟我的互動式 AI 協作 dashboard"
         src="dist/summary-light.svg">
  </picture>
</a>
```

Heatmap 可使用相同 `<picture>` 結構，將檔名改為
`heatmap-{light,dark}.svg`。GitHub README 不會執行 JavaScript，因此
Profile 仍顯示 SVG，點擊連結後才開啟 `dashboard.html`。

使用 GitHub Pages 託管 dashboard：

1. 將 `README.md` 與 `dist/` push 到 Profile repository 的 `main` branch。
2. 開啟 **Settings → Pages**。
3. 在 **Build and deployment** 選擇 **Deploy from a branch**。
4. 選擇 **main**、**/ (root)**，再按 **Save**。
5. 開啟
   `https://USERNAME.github.io/USERNAME/dist/dashboard.html`。

新的 Pages deployment 可能在數分鐘內暫時回傳 404。等待 Pages workflow
完成後，再重新載入大小寫完全一致的 URL。若仍為 404，請確認 Pages 使用
`main` 與 `/ (root)`，而且 push 的 commit 中確實有
`dist/dashboard.html`。

## 會產生哪些內容

下方使用 synthetic data，展示完整輸出系列：

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/WenyuChiou/ai-profile/main/docs/assets/summary-sample-dark.svg">
  <img alt="使用 synthetic data 的 AI 協作 summary card" src="https://raw.githubusercontent.com/WenyuChiou/ai-profile/main/docs/assets/summary-sample-light.svg">
</picture>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/WenyuChiou/ai-profile/main/docs/assets/badge-sample-dark.svg">
  <img alt="使用 synthetic data、由 Git provenance 驗證的 AI-assisted 比例 badge" src="https://raw.githubusercontent.com/WenyuChiou/ai-profile/main/docs/assets/badge-sample-light.svg">
</picture>

六個 SVG 都是靜態且可直接放入 GitHub。`dashboard.html` 是 self-contained
的 provider-filterable view，支援 light、dark 與 system themes，不會載入
外部 script、font、tracker 或 API。`profile.json` 與所有 renderer 使用
相同、已驗證的公開 aggregate contract。

## 宣告 AI 參與

已知 AI co-author identities 會自動辨識。其他工具或更完整 attribution
可在 commit message 的空白行後加入一個連續 `AI-*` trailer block：

```text
feat: add aggregation service

AI-Provider: Anthropic
AI-Model: Claude-Sonnet
AI-Tool: Claude-Code
AI-Role: implementation, documentation
AI-Mode: AI-Assisted
AI-Reviewed-By: Human
```

同一個 commit 中若有另一位 AI actor，請直接重複 `AI-Provider:`，actor
group 之間不要留空白行。因此一個 commit 可以同時是 1 個 unique
AI-attributed commit 與多個 actor presences。只有明確的人類獨立 commit
才使用 `AI-Mode: Human-Only`。

## 隱私

- CLI 不會進行網路呼叫、不上傳 repository data，也不傳送 telemetry。
- 公開資產會包含 UTC generation date，也可能包含 aggregate counts、
  公開 provider names 與 evidence totals；repository activity dates
  只會來自 `full` repositories。
- 公開資產絕不包含 repository names 或 paths、organization names、
  branches、commit SHAs 或 messages、raw trailers、prompts 或 email
  addresses。
- `aggregate` 是公開預覽；commit 任何產生資產前都應先檢查。
- Aggregate-only 是 identity redaction，不等於 anonymity；重複發布可能
  揭露統計何時改變。
- 不可發布或同步 `.aiprofile`；其中包含私有 paths、identities、
  repository identifiers 與本機 salt。

完整內容請見
[隱私模型](https://github.com/WenyuChiou/ai-profile/blob/main/docs/PRIVACY.md)。

## 指標與目前限制

- **AI-attributed commits** 是至少含一個明確 AI actor presence 的 unique
  commits。
- **Actor presences** 計算 commit 內不同 provider/tool 的參與；provider
  totals 可能大於 unique commit totals。
- **Unknown** 永遠與 human 分開。
- Evidence quality 為
  `verified > declared > imported > inferred > unknown`。
- Scan 只涵蓋目前 `HEAD` 可到達的 commits，不會掃描所有 branches。
- 尚未支援使用 SHA-256 object format 的 Git repositories。
- Bot-authored commit 不在 author-identity scan 範圍內，除非刻意把 bot
  address 加入設定；部分 bot 加 human co-author 的歷史因此可能不會出現。
- 沒有明確 Git 證據的歷史 AI 使用會維持 unknown；絕不使用程式碼風格
  重建 attribution。

## 說明、貢獻與授權

執行 `aiprofile --help` 或 `aiprofile COMMAND --help`。Bug 與功能建議請使用
[GitHub Issues](https://github.com/WenyuChiou/ai-profile/issues)；安全問題請依
[security policy](https://github.com/WenyuChiou/ai-profile/blob/main/SECURITY.md)
私下回報。

歡迎貢獻，請參考
[CONTRIBUTING.md](https://github.com/WenyuChiou/ai-profile/blob/main/CONTRIBUTING.md)。
專案採用
[MIT License](https://github.com/WenyuChiou/ai-profile/blob/main/LICENSE)；
vendored icons notices 位於
[THIRD_PARTY_NOTICES.md](https://github.com/WenyuChiou/ai-profile/blob/main/THIRD_PARTY_NOTICES.md)。
