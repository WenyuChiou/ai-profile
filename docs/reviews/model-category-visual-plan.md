# 模型類別貢獻視覺化計畫

日期：2026-08-04
狀態：候選實作與本地獨立驗收完成；等待 Ubuntu CI、跨平台 onboarding 與發布 gate
基準：v0.4.10 Public Beta（目前版本維持可發布，不因本計畫自動變更）

## 目的與現況

使用者希望圖表能回答「哪些模型類別實際出現在 AI 協作紀錄中」。目前
ACE event 已保存 `model` / `model_raw`，但 `aggregate.py` 只建立 provider
聚合，`VizStats`、`profile.json`、summary SVG 與 dashboard 都沒有 model
維度。因此 v0.4.10 不能誠實地聲稱已展示模型貢獻；在 renderer 內由
provider、tool、commit message 或程式碼風格猜模型，均違反架構與隱私邊界。

本計畫把模型類別視為新的公開 aggregate 維度，而不是把它塞進 provider
欄位或用顏色暗示。

目前候選分支已依本計畫落地 `ModelAgg`、`ModelRow`、公開 JSON、summary
ledger、dashboard model panel、synthetic sample 與 clean-wheel smoke。這些
變更尚未改寫已發布的 v0.4.10 assets；在 Ubuntu artifact、跨平台 onboarding、
privacy、browser 與獨立 review 全部通過前，v0.4.10 仍是唯一正式 Public Beta。

## 研究得到的設計約束

- Nanako0129 的公開 profile 以「group by model rather than client」說明
  分組維度必須對準消費者真正想知道的對象；同一個 model 可以透過不同
  client 使用。這個資訊架構可採用，但不複製其個人主機、專案、token 或
  terminal 裝飾。
- TokenBar 把 app/provider 篩選與 model view 分開；這提醒我們 provider、
  tool/client、model 不是同一個欄位，不能把一種分組冒充另一種。
- Primer、Carbon 與 Vega-Lite 的共同原則是語意 token、直接標籤、明確
  domain/encoding、文字替代與可及性；因此模型類別只能由已驗證的公開
  aggregate rows 呈現，不能靠漸層、3D 或 hover-only legend。
- 現有 Flat Evidence Ledger 的地形圖以「每天 unique total commits 的
  高度 + AI share 的色階」為語意。provider/model 都不能改變柱高，否則
  一個 commit 多個 actors 會被重複放大。

## 決策（候選 v0.5.0）

### 新的公開契約

新增 frozen `ModelRow`，欄位與 provider row 對稱但語意獨立：

```text
ModelRow
  category: closed public slug
  display_name: schema-owned label
  attributed_commits: distinct commits with >=1 explicit event in category
  actor_presences: AI/mixed event records in category
  active_days: author-local dates with >=1 event in category
```

`VizStats` 新增排序後的 `models` tuple 與 `model_count`。`profile.json`、
dashboard 與 summary 都使用同一份 validated rows。這是公開 visualization
contract 的 additive minor change，依 ADR-012 將 ACE/public contract version
提升至 `0.3.0`；舊 `0.2.x` SQLite events 必須仍可讀，新掃描寫入新版本。
若實作發現 ACE event version 與 public aggregate version 必須分離，應新增
明確的 `viz_schema_version` 欄位並另立 ADR，不得偷偷重用或誤標版本。

### 模型類別 vocabulary

第一版只發布受控、低基數的 family labels：

```text
claude, gpt, gemini, llama, mistral, deepseek, qwen, grok, kimi,
other, unknown
```

`model` 缺失時進入 `unknown`；有明確 model 但不符合受控 prefix/alias 時
進入 `other`。只根據 ACE event 的 canonical model 做 deterministic
normalization；不使用 provider、tool、作者、commit message、source style
或任何歷史推測。`model_raw` 永遠留在 local-only aggregation details，
不得進入 ModelRow、JSON、SVG、HTML、URL 或 alt text。

### 不混淆的計數語意

- `model.attributed_commits` 是 category 對 commit 的 distinct count，跨
  categories 可以重疊；不可與 `totals.ai_attributed_commits` 相加。
- `model.actor_presences` 是事件/presence count；應與全部 model rows 的
  presences 相加後等於 `totals.ai_actor_presences`，包含 `unknown` model。
- `model.active_days` 是 author-local date set 的 cardinality，不是 commit
  數，也不是 provider count。
- 一個 commit 同時有兩個 provider 或兩個 model categories 時，兩個 row
  各自可 credited；headline unique commit 仍只算一次。
- `unknown` model 永遠保持獨立，不轉成 human，也不因 provider 已知而猜成
  某個 model family。

## 視覺與互動邊界

### Summary SVG

在現有 Flat Evidence Ledger 下新增一個小型 `Model contribution` ledger，
採用 top-4 rows + `+N model categories not shown`，以文字、數字、百分比及
短 bar 同時呈現；不加入立體地形、透視、漸層、動畫或第九個輸出。Model
rows 應與 provider rows 分欄或以清楚分隔的第二 rail 排版，保持 830px、
11/12/13/16/38 type scale、4px spacing、light/dark paired bytes。

daily terrain 維持 current two-channel semantics。它不顯示模型日序列，因
目前 daily contract 沒有 model counts；在 card footer/legend 明確寫出
model ledger 是 all-time explicit model evidence。新增 daily model filter
必須等下一個 contract 把 `(date, category)` 的 distinct counts 定義完整。

### Dashboard

新增與 provider panel 平行的 model-family ledger，沿用同一份 `VizStats`。
現有 All AI / provider filters 維持不變；本版本不提供 model filter 改寫
headline 或 daily chart，避免用沒有交叉分組資料的 renderer 計算假統計。
之後若要加入 model filter，必須先提供 provider×model×date 的 validated
aggregate rows 與相應測試。

### 可及性與樣式

- category 名稱、數字、分母及「non-exclusive」文字必須可在無色彩、無 hover
  的情況下閱讀；mark 只是輔助，不是唯一語意。
- model marks 使用小型、受控 token；不使用品牌 logo 或外部字體資源。
- 文字至少保持現有 WCAG gates；SVG allowlist、CSP、無 external refs、
  deterministic bytes 全部不變。

## 實作順序（red-first）

1. 新增 ADR（建議 ADR-027）與 schema/architecture/mvp/ROADMAP/CHANGELOG
   的契約敘述，先寫 model category vocabulary、privacy 和 count units。
2. 先寫 failing tests：normalization boundary、one commit/multiple model
   categories、missing model unknown、unknown≠human、aggregate-only
   redaction、model-row validation/ranking、JSON parity、privacy canary。
3. 在 aggregate layer 加入 policy-free `ModelAgg` 與 model SQL projection；
   只讀 ACE canonical model，不能讓 renderer 讀 SQLite 或 raw events。
4. 在 privacy chokepoint 建立 `ModelRow`，套用與 provider 相同的 publication
   levels、closed display vocabulary 與 exact-type validation。
5. 更新 summary/dashboard 兩個純 renderer；保持 provider / terrain 的既有
   semantics，新增 model panel 的高度、overflow、zero/aggregate-only 狀態。
6. 只用 sanctioned scripts regenerate snapshots/assets；跑 full pytest、
   Ruff、README parity、double-render、SVG allowlist、CSP、privacy sweep、
   wheel smoke、browser QA。
7. 用 synthetic fixture 與真實 profile 做 hand-derived reconciliation：
   model rows、provider rows、unique commits、presences、evidence 各自
   對帳；確認沒有把 provider/client/model 三種分母混在一起。

## 明確不做

- 不從 source style、prompt、commit message、tool 或 provider 推斷 model。
- 不發布 raw model names、模型版本字串、帳號、repo/path、SHA、email 或
  prompt；不在 public HTML 內保留 raw model 欄位。
- 不把 `unknown` model 改成 human，不把 model rows 加總成 unique commits。
- 不新增 runtime dependency、network font、hosted API、plugin loader、
  interactive 3D、animated terrain 或 generic AI skill score。
- 不在 v0.5.0 同時承諾 model-by-date filter；那是有完整 cross-dimension
  contract 後的後續版本。

## Promotion gate

目前 v0.4.10 維持 `GO — PUBLIC BETA` 的既有 release evidence。模型類別
功能只有在新版本完成 schema/ADR、red-first tests、公開隱私掃描、跨平台
wheel smoke、瀏覽器視覺 QA、snapshot byte stability、獨立 gate review，且
無未解 Critical/High 後，才能另行 promotion。若任何分母或 privacy boundary
無法從 raw logs/artifacts 重新計算，結論必須是 `NO-GO`，不可用畫面美觀掩蓋
資料契約缺口。
