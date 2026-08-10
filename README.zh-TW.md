<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/WenyuChiou/ai-profile/main/docs/assets/banner-dark.svg">
  <img alt="" src="https://raw.githubusercontent.com/WenyuChiou/ai-profile/main/docs/assets/banner-light.svg" width="100%">
</picture>

# ai-profile

## 讓你的 AI 協作有證據可查。

`ai-profile` 會把本機多個 Git repository 中明確記錄的 provenance，
轉換成適合 GitHub Profile 的隱私安全卡片與可依 provider 篩選、含 provider
ledger 的 dashboard；
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
- **本機優先的隱私：** CLI 的 scan、aggregate、refresh 與 render 都在你的電腦執行；
  repository identity 不會進入公開資產。
- **可直接放上 Profile：** 一次 render 會產生支援主題的 SVG 卡片、
  self-contained dashboard 與可供機器讀取的公開摘要。

`ai-profile` 不是 AI code detector。沒有證據的 commit 會維持
`unknown`（介面會顯示為**未歸屬**），不會被偷偷算成人類完成，也不會被指派給
任何 provider。若希望記錄未來 commit 的 AI 參與，請加入 `AI-*` trailers。

## 真實 GitHub Profile 範例

下方卡片使用維護者的真實公開 aggregate data。點擊即可開啟可依 provider
篩選的 dashboard；卡片會顯示明確的 provider 參與與 evidence 總數。

<a href="https://wenyuchiou.github.io/WenyuChiou/dist/dashboard.html">
  <picture>
    <source media="(max-width: 600px) and (prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/WenyuChiou/WenyuChiou/main/dist/badge-dark.svg">
    <source media="(max-width: 600px)" srcset="https://raw.githubusercontent.com/WenyuChiou/WenyuChiou/main/dist/badge-light.svg">
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/WenyuChiou/WenyuChiou/main/dist/summary-dark.svg">
    <img alt="開啟 Wenyu Chiou 的互動式 AI 協作 dashboard" src="https://raw.githubusercontent.com/WenyuChiou/WenyuChiou/main/dist/summary-light.svg">
  </picture>
</a>

這張卡片呈現持續的 AI 協作（active AI days 與 12 週扁平活動矩陣）、
跨 AI providers 的廣度，以及每個數字背後的明確 evidence 總數。它是根據
宣告 Git evidence 的紀錄，不是技能評分。

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

## 每日自動更新

請選擇其中一種方式。
Private 與 `aggregate_only` repositories 應留在自己的電腦；
只有所有來源 repositories 都已公開時，
才使用 GitHub Actions。

```bash
# 立即更新所有已設定、未 excluded 的 repositories。
aiprofile refresh --out dist
aiprofile refresh --out dist --dry-run

# 或安裝每日本機工作（電腦本地時間 05:37）。
aiprofile schedule install --profile-repo /path/to/USERNAME --time 05:37
aiprofile schedule status
aiprofile schedule remove
```

### 更新所有已設定 repositories

`refresh` 會逐一路徑重新 scan，再 aggregate，
並寫入相同八個檔案。Aliases 不會造成重複 scan，
`excluded` repositories 仍維持排除。任何 scan、設定、隱私或 render 失敗，
都不會發布新一代輸出。`--dry-run` 只列出八個檔案中哪些會改變，
不會改變 configuration、publication policy、已記錄的 database/WAL content，
也不會改變 output assets。它可能建立或使用 advisory lock；
SQLite 讀取已 commit 的 WAL content 時，也可能更新暫時性的 `-shm`
coordination bytes；兩者都不是公開資料。

若兩筆設定解析到相同路徑，卻使用不同的 `repository_uid`，refresh 會在
scan 或讀取 cached aggregates 前拒絕整次執行。請保留 `scan` 建立的 UID；
不要把 UID 複製到其他 entry，也不要自行建立替代值。

同一時間只能有一個 refresh 使用某個 `AIPROFILE_HOME`。極少數 filesystem
錯誤若造成輸出 rollback 不完整，CLI 會明確說明可能留下部分資產或 recovery
backup；commit 前請先檢查輸出。

### Private 或本機 repositories：原生 scheduler

`schedule install` 會建立 OS 原生的 user job：
Windows 使用 Task Scheduler、macOS 使用 launchd，
Linux 使用 systemd user timer。它每天更新 `<profile-repo>/dist`；
預設只 stage 八個產生路徑，只在 bytes 改變時 commit，
再使用 repository 既有的 Git authentication；只有 remote 仍等於記錄的
parent 時才會 push。
Push mode 要求單一 fetch destination 與相同的單一 push destination；
多個或不同的 push URL 會在 refresh 前 fail closed。已捕捉的 destination
會綁定到 private、isolated Git context 內的固定 alias；push 與驗證不會把
URL 放進 argv，也不受稍後 repository、global、`insteadOf` 或
`pushInsteadOf` 變更改向。支援不含 credentials、query 或 fragment 的
HTTPS、SSH/SCP、Git、file URL 或 local path。Local path 會先以 Profile
repository 為基準解析，再建立 isolated context。Shallow 與 partial clone
會在 refresh 前被拒絕，因為排程發布需要完整的本機 Git history。
請使用 credential manager、askpass 或 SSH agent；刻意不支援 embedded password
與 authorization header，也不轉送 ambient proxy variables。
本工具不會持久保存或記錄 credentials。加入 `--no-push` 仍會建立並推進本機 exact-eight commit，
但不會 push 到 remote；`--dry-run` 可預覽安裝而不改變 scheduler state。

User scheduler 與電腦必須可用。
Windows 與 systemd 會依原生設定補跑錯過的工作；
launchd 不會補跑電腦關機期間錯過的時間點。
Detached branch、已改變的 branch state、protected branch 與被拒絕的 push
都會 fail closed。Scheduler commit 是機械式 commit，
刻意不執行使用者的 commit hooks 或 signing。

可 push 的執行開始前，記錄的 remote branch 必須與本機 `HEAD` 完全一致；
請先自行同步刻意建立的 local commits。Push 失敗後，會先安全復原中斷的
branch update 與 exact-eight index；只有 branch、parent、tree 與 remote
都未改變時，才會從同一個 private pending commit 重試。實際 push 使用綁定
該 parent 的 exact-old lease，並在回報成功或清除 retry state 前重新確認
remote 已位於 immutable commit。Private retry record 只保存 destination 的
SHA-256 commitment，不保存 URL 本身。
不同 homes 若指向同一個 Profile，會由該 Profile 的 Git metadata lock
序列化；建立 commit 前也會核對產生檔案確實來自剛完成的 refresh。

請從會持續保留的 Python environment 安裝 scheduler。若移動、移除或升級
該 interpreter 或 virtual environment，請重新執行 `schedule install`，
並以 `schedule status` 確認。

### Public repositories：GitHub Actions

若 Profile 的所有來源都是 public repositories：

1. 將 [`docs/templates/profile-refresh-caller.yml`](docs/templates/profile-refresh-caller.yml)
   複製到 Profile repository 的 `.github/workflows/profile-refresh.yml`。
2. 編輯明確的 public `owner/repo` 清單。把 identity email payload 設為
   repository secret `AIPROFILE_IDENTITIES`；絕對不要放在 `with:`。
3. 在 **Settings → Pages** 將來源設為 **GitHub Actions**，再到
   **Actions → Daily ai-profile refresh → Run workflow** 手動執行一次。

Template 每天 05:37 UTC 執行，也支援手動 dispatch。
它以 commit `9c4f276cb437f1866a2c1b407efe54d3790ce811`
固定 reusable workflow，安裝確切的 `ai-profile-cli==0.7.0`，
並在 scan 前拒絕非公開來源。Pages 只部署該次執行產生的
確切 `published-sha`。Template 只使用 `GITHUB_TOKEN`，不提供 PAT fallback。
GitHub-hosted automation 不是本機優先處理：
它只 clone 你列出的 public repositories，並一律視為 `full`。
只要有 private 或 `aggregate_only` 來源，就使用本機 scheduler。

Branch protection 可能拒絕直接 commit 資產。
Public repository 若 60 天沒有 repository activity，
scheduled workflow 可能停用；fork 必須啟用 Actions。
Organization Actions allowlist 也必須允許固定版本的 actions
與 reusable workflow。`GITHUB_TOKEN` 建立的 commit
不會觸發一般 push workflows 或 Pages build，
因此 caller 會在同一次 run 明確部署 Pages。
請只使用一個 caller，不要建立會重疊執行的 matrix。

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

手動發布時，請依下列步驟使用 GitHub Pages 託管 dashboard。若使用上方的每日
Action，Pages source 請維持 **GitHub Actions**，並略過以下 branch-source
步驟。

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

summary card 與 dashboard 共用平面的 Editorial Signal 視覺系統：安靜的
紙張與墨色表面、藍色協作訊號、暖黃色 evidence cue，以及只用來改善閱讀
節奏的小型對齊線；活動不會被包裝成 3D 分數或裝飾場景。

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/WenyuChiou/ai-profile/main/docs/assets/summary-sample-dark.svg">
  <img alt="使用 synthetic data 的 AI 協作 summary card" src="https://raw.githubusercontent.com/WenyuChiou/ai-profile/main/docs/assets/summary-sample-light.svg">
</picture>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/WenyuChiou/ai-profile/main/docs/assets/heatmap-sample-dark.svg">
  <img alt="使用 synthetic data 的 commit 活動 heatmap；深淺代表 commit 量，色相代表 AI 比例" src="https://raw.githubusercontent.com/WenyuChiou/ai-profile/main/docs/assets/heatmap-sample-light.svg">
</picture>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/WenyuChiou/ai-profile/main/docs/assets/badge-sample-dark.svg">
  <img alt="使用 synthetic data、由 Git provenance 驗證的 AI-assisted 比例 badge" src="https://raw.githubusercontent.com/WenyuChiou/ai-profile/main/docs/assets/badge-sample-light.svg">
</picture>

六個 SVG 都是靜態且可直接放入 GitHub。`dashboard.html` 是 self-contained
的 provider-filterable view，包含 provider ledger，支援 light、dark 與 system
themes，不會載入
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

`AI-Provider` 宣告會正規化為 canonical provider identity（通常以 company 為
導向）。dashboard 可能改以更容易辨識的 product display name 顯示：
`AI-Provider: Anthropic` 會顯示為 **Claude**。這只是標籤對應，不會改變
aggregation 或 counts。

若有 `AI-Model`，canonical value 會對應到小型、由 schema 控制的 model family
vocabulary（例如 `Claude-Sonnet` → **Claude**），並以已驗證的 machine-readable
evidence 保留在 `profile.json`。Family commit counts 刻意採 non-exclusive，
actor presences 與 active days 仍是分開的指標。沒有 model 宣告會維持
**Unknown**；raw model strings 不會進入公開資產。

## 隱私

- Scan、aggregate、refresh 與 render 不會進行網路呼叫，也不傳送 telemetry。
  選用的本機 scheduler 可能透過 credential manager、askpass 或 SSH agent
  執行 `git push`；`ai-profile` 不會持久保存或記錄 credentials。
- 選用的 public Action 在 GitHub-hosted runner 執行，只 clone 明確列出的
  public repositories。Identity emails 透過 secret 傳入，不會寫入公開資產或
  default workflow logs。
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
- **`profile.json` 的 model-family rows** 計算明確 canonical `AI-Model`
  evidence；一個 commit 可以同時貢獻給多個 family row，但不會增加 unique
  AI-attributed commit headline。
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
