# 找候選專案（階段 1）

這個階段只找**方向對**的專案。活躍度、回應速度、新手 issue 數這些細項，都留給階段 2、3 再檢查。

## 目錄
1. 從學生側寫找專案
2. 特殊情況：工具不開源、工具太大
3. GitHub 搜尋語法（用範圍粗篩）
4. 新手專案彙整網站
5. 確認貢獻說明
6. 練習 git 流程

## 1. 從學生側寫找專案

依側寫的四欄，大致照這個優先順序：

1. **痛點**：學生抱怨的工具如果是開源的，它本身就是候選。到它的 issue 裡搜尋這個痛點，有人回報過的話，學生一開始就有一個很具體的切入點。
2. **平常在用的工具、套件、App**：學生懂使用者的角度，碰到困難也比較不會放棄。可以問：「你的作業或專案的 requirements.txt / package.json 裡有哪些套件？」
3. **想學的技術**：那個技術本身，或用它寫成的中型專案（見 `interest-examples.md` 的「想學的技術」一節）。
4. **興趣主題**：用 GitHub topic 或關鍵字搜尋（見第 3 節）。
5. **新手專案彙整網站**：上面都找不到時再用（見第 4 節）。

## 2. 特殊情況

**學生在用的工具不是開源的**（Notion、Spotify、Instagram…）
- 找開源的替代品，例如筆記類工具有很多開源替代品
- 找圍繞它的開源周邊：非官方的 API 套件、匯出或備份工具、外掛

**學生在用的工具太大**（VS Code、Python、Chrome…）
- 往生態系找：擴充套件、外掛、主題、相關的小工具。規模比較小、維護者比較容易回應，也一樣貼近學生的使用經驗
- 超大型專案本身（數萬 star、上千位貢獻者）review 慢、新手 issue 競爭激烈，除非它有完整的新手計畫，否則放在後面

## 3. GitHub 搜尋語法（用範圍粗篩）

這一階段只用**範圍**縮小候選，不要加太多條件。到 github.com/search，類型選 Repositories：

```
topic:music language:python stars:100..5000
guitar tab in:name,description,topics stars:50..5000
```

- `topic:` 主題標籤，例如 `game`、`machine-learning`、`cli`、`education`
- `language:` 主要語言（對應學生會的語言）
- `stars:100..5000` 中型專案通常最適合第一次貢獻：有人在用，但不至於太擁擠。範圍可以依情況調整
- `關鍵字 in:name,description,topics` 用興趣或痛點的關鍵字搜尋

在特定專案裡找痛點有沒有人回報過（類型選 Issues）：

```
repo:OWNER/REPO is:issue 關鍵字
```

最近有沒有更新、新手 issue 多不多這些條件，留到階段 2、3 再看。

## 4. 新手專案彙整網站

- **goodfirstissue.dev**：依語言整理有 good first issue 的熱門專案
- **up-for-grabs.net**：專案主動登記「歡迎新手」的清單，可依標籤篩選
- **GitHub Topics**：`github.com/topics/good-first-issue`

這些清單上的專案通常比較熱門，新手 issue 搶的人也多；清單也可能有過時的條目，健康度在階段 2 檢查。

## 5. 確認貢獻說明

推薦前唯一要確認的事。有貢獻說明，代表專案有在開放、也準備好接受外部貢獻；沒有的不推薦。以下兩種都算：

- **CONTRIBUTING 檔案**：放在根目錄、`.github/` 或 `docs/`
- **README 裡的貢獻段落**：標題像是「Contributing」「How to contribute」「Contributions welcome」。只有「Contributors」（貢獻者名單）不算

```bash
python scripts/analyze_repo.py quick OWNER/REPO OWNER/REPO ...
```

腳本會一次列出每個專案的 GitHub 連結、簡介、語言、star 數，以及貢獻說明是 CONTRIBUTING 檔案、README 段落，還是都沒有。腳本跑不了時，到 GitHub 專案頁面手動找。

## 6. 練習 git 流程

推薦完專案後，如果學生從沒送過 PR，順帶提一句：可以先在 **firstcontributions/first-contributions** 這個練習用的 repo 走一遍。它就是設計來讓人練習送第一個 PR 的，練完再碰真正的專案，緊張感會少很多。

要讓學生知道：練習 repo 的 PR 不算真正的開源貢獻，目標還是真實專案。
