<div align="center">

# oss-first-contribution

**陪開源新手從零開始，一路走到第一個 PR 被合併的 AI 助手 skill。**

[![test](https://github.com/Howardisme/oss-first-contribution/actions/workflows/test.yml/badge.svg)](https://github.com/Howardisme/oss-first-contribution/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-blue.svg)
![Works with Claude Code, Codex and Copilot](https://img.shields.io/badge/works%20with-Claude%20Code%20%7C%20Codex%20%7C%20Copilot-8A2BE2.svg)

[English](README.md) | 繁體中文

</div>

---
**開源不看你的頭銜，只看你的程式碼**

很多想參與開源的新手，還沒寫下第一行程式就卡住了：不知道該選哪個專案、不確定 PR 送出去會不會有人看、也不知道什麼樣的題目適合當第一次。`oss-first-contribution` 是一個給 AI 程式助手用的 [skill](https://agentskills.io)，像一位有耐心的資深貢獻者，帶你走完整個過程。

## 特色

- **從需求角度出發，找到真正適合貢獻的專案。** 先聊興趣、日常的痛點、想學的技術，再找對應的專案。人會持續貢獻的，往往是自己真的在用的東西。
- **確認專案是不是真的歡迎新手。** 內附的腳本會幫專案打分數：外部 PR 被合併的比例、維護者真人（不是機器人）多快回應、維護者永續性（bus factor）等。也會標出像「沒連到已核可 issue 的 PR 會被自動關閉」這類貢獻門檻。
- **找到合適的第一個題目。** 列出沒人認領的 issue、缺少的翻譯或測試，再讀留言檢查有沒有人說過「I'll take this」，避免撞題。
- **帶著實際動手。** 認領 issue、fork、建環境、讀懂陌生的程式、照專案範本寫 PR，最後最重要的，發出一支 good PR。
- **讓你為自己的作品負責。** 助手會解釋每一處改動，讓你在 review 時答得出來，也會遵守每個專案的 AI 政策。
- **自訂指標。** 指標權重、門檻、標籤、目標翻譯語系都在同一個設定檔。你也可以加上自己在乎的主觀指標，例如「這裡學不學得到東西？」

## 快速開始

> [!IMPORTANT]
> **開始前先確認兩件事：**
>
> 1. **裝好 [Python 3.8+](https://www.python.org/downloads/) 和 [GitHub CLI](https://github.com/cli/cli#installation)，並執行 `gh auth login` 登入。** 沒有登入，GitHub 每小時只給 60 次請求，大約只夠評估一個專案。
> 2. **用 Codex 的話，看到網路存取的詢問時請核准。** Codex 的沙盒預設不開網路，但分析腳本要連到 `api.github.com`。想一直開著，請看[開啟網路](INSTALL.zh-TW.md#codex開啟網路)。

**Claude Code**

```bash
claude plugin install oss-first-contribution --marketplace Howardisme/oss-first-contribution
```

**Codex**

```bash
codex plugin marketplace add Howardisme/oss-first-contribution
codex plugin add oss-first-contribution@oss-first-contribution
```

**GitHub Copilot**（手動加入 skill 資料夾）

```bash
git clone https://github.com/Howardisme/oss-first-contribution.git
cd oss-first-contribution
mkdir -p ~/.copilot/skills
cp -r skills/oss-first-contribution ~/.copilot/skills/
```

裝好後開一個新的對話，跟助手說：

> 我是開源新手，想完成第一個開源貢獻。

聊到想參與開源時 skill 會自動啟用。Copilot 請先切到 **Agent** 模式，執行 `analyze_repo.py` 前它會先詢問，按允許即可。

Windows 指令、更新方式、手動安裝到 Claude Code 或 Codex、Codex 的 token 設定，請看 [INSTALL.zh-TW.md](INSTALL.zh-TW.md)。

## 運作方式

skill 帶你走七個階段。每個階段結束前，你都要先做出選擇才往下走。

| 階段 | 做什麼 |
|---|---|
| **0 認識你** | 先說明為什麼要從每天在用的東西下手，再依序聊興趣 → 痛點 → 想學什麼 |
| **1 找候選專案** | 推薦 5 個專案，每個附上連結、白話摘要和適合的理由。只推薦有貢獻說明（`CONTRIBUTING` 檔案或 README 段落）的專案 |
| **2 評估專案** | 你先選自己在乎的指標，再由腳本分三層評估：基礎資訊（不計分）、客觀指標（計分）、由助手附證據判斷的主觀指標 |
| **3 找題目** | 列出沒人認領的 issue（由新到舊），檢查口頭認領，推薦 2–3 個題目並說明理由 |
| **4 動手做** | 認領 issue、fork、建環境、看懂程式、修改、跑測試 |
| **5 送 PR** | 在 GitHub 網頁開 PR、照專案的 PR 範本填寫、看懂 CI 和機器人留言、回應 review |
| **6 收尾** | 整理 fork、回顧，回來這裡分享你的經驗 |

### 評估指標

| 面向 | 指標 | 預設權重 |
|---|---|---|
| 活躍度 | 距離上次 commit（分級，14 天內為「極度活躍」）、近期 commit 數、近期合併 PR 數 | 15 |
| 對外部貢獻者友善 | 外部 PR 合併率、外部 PR 合併天數、維護者真人首次回應時間 | 50 |
| 維護者回應 | Issue 回應率、首次回應時間、Issue 關閉/新增比 | 20 |
| 新手入口 | 有新手標籤、沒人認領的 issue 數 | 5 |
| 維護者永續性 | Bus factor、核心成員人數 | 10 |

幾個讓分數更可信的設計：

- **機器人和自動關閉不算回應。** 只算核心成員的真人回覆。很多專案會自動關閉不符流程的 PR，算進去會讓專案看起來「秒回」。
- **員工不算外部貢獻者。** 經常 commit 的人會被當成核心成員，即使他沒公開組織成員身分。
- **底線。** 外部 PR 合併率低於 30%，或 issue 回應率低於 50% 時，不管總分多高，結論最多只到「可以，但要注意」。

完整定義在 [`references/metrics.md`](skills/oss-first-contribution/references/metrics.md)，所有門檻都可以在 [`config.json`](skills/oss-first-contribution/config.json) 調整。

## 參與貢獻

歡迎所有形式的貢獻：

- **分享經驗。** 完成一次開源貢獻後，到 [`experiences/`](experiences/) 寫下你的經驗：選了哪個專案、卡在哪裡、怎麼解決的。
- **回報問題、提出功能**，請用 issue 範本。
- **挑一個 issue 來做**，從標了 [`good first issue`](https://github.com/Howardisme/oss-first-contribution/labels/good%20first%20issue) 的開始。

專案結構、怎麼跑測試等詳細說明，請看 [CONTRIBUTING.zh-TW.md](CONTRIBUTING.zh-TW.md)。

## 致謝

評估指標參考了 [CHAOSS](https://chaoss.community) 在開源社群健康度上的研究。

## 授權

[MIT](LICENSE)
