# 從 fork 到 PR 的完整流程

## 目錄
1. 一次性設定
2. 開始一個貢獻
3. 建開發環境
4. Commit
5. 送出 PR
6. 回應 review
7. 同步主線、解決衝突
8. 常見問題

指令中的 `OWNER/REPO` 是原專案，`YOU` 是學生的 GitHub 帳號。

---

## 1. 一次性設定

```bash
git config --global user.name "你的名字"
git config --global user.email "你的 GitHub email"
```

- 執行前先用 `git config --global user.email` 看看有沒有設定過。已經設成其他 email（例如工作電腦上的公司 email）的話不要覆蓋：等 clone 完，在專案資料夾裡執行同樣的指令、拿掉 `--global`，只對這個專案生效。
- email 要跟 GitHub 帳號綁定的一樣，貢獻才會算在帳號上。不想公開 email 可以用 GitHub 設定頁提供的 `ID+username@users.noreply.github.com`
- 推薦安裝 GitHub CLI（`gh`）並執行 `gh auth login`：fork 可以用指令完成，分析腳本也會自動使用它的登入（開 PR 建議用 GitHub 網頁，見第 5 節）

## 2. 開始一個貢獻

```bash
# fork：在 GitHub 頁面右上角按 Fork，或：
gh repo fork OWNER/REPO --clone
cd REPO

# 沒用 gh 的話：
git clone https://github.com/YOU/REPO.git
cd REPO
git remote add upstream https://github.com/OWNER/REPO.git

# 確認 remote：origin 是你的 fork，upstream 是原專案
git remote -v

# 從最新的主線開新 branch（主線可能叫 main 或 master，看專案）
git fetch upstream
git switch -c fix-issue-123 upstream/main
```

**branch 名稱**用簡短描述，例如 `fix-typo-install-docs`、`add-tests-utils`、`zh-tw-translation`。**不要直接在 main 上改**：之後要同步主線或同時做第二個 PR 時會很痛苦。

## 3. 建開發環境

原則：環境不是這次要學的重點，不要讓它卡住學生。遇到錯誤就直接給解法。

**去哪裡找安裝步驟**：先看 README（通常有 Installation、Getting started、Development 段落），再看 CONTRIBUTING 或文件網站。

**常見問題**

| 狀況 | 解法 |
|---|---|
| Python 套件裝到系統環境、版本衝突 | 先建虛擬環境：`python -m venv .venv`，再啟用（macOS/Linux：`source .venv/bin/activate`；Windows：`.venv\Scripts\activate`） |
| Node 版本不對 | 看專案的 `.nvmrc` 或 `package.json` 的 `engines`，用 nvm 切換到指定版本 |
| 指令在 Windows 上跑不了 | 很多專案預設 macOS/Linux，改用 WSL 通常最快 |
| 缺少系統套件（編譯器、資料庫等） | 照錯誤訊息裡提到的名稱安裝；README 沒寫的話，記下來之後可以回報 |
| 測試一開始就有失敗 | 先確認是不是環境問題；不是的話記下來，之後跟維護者說明「這些測試在我改之前就失敗了」 |

**怎麼裝都裝不起來時**

- 專案根目錄有 `.devcontainer/` 資料夾：可以用 VS Code 的 Dev Containers，或在 GitHub 專案頁面按 Code → Codespaces 開一個雲端環境，環境都已經設定好
- 專案有 `Dockerfile` 或 `docker-compose.yml`：用 Docker 跑
- 只是改文件或翻譯：很多時候不需要完整環境，直接在 GitHub 網頁上編輯也可以

**環境建好後，先跑一次現有測試**（指令通常寫在 README 或 CONTRIBUTING，例如 `pytest`、`npm test`、`go test ./...`），記下結果。如果本來就有測試失敗，之後才知道不是自己造成的。

## 4. Commit

```bash
git status            # 看改了哪些檔案
git diff              # 看具體改了什麼
git add 路徑/檔案      # 只加這次相關的檔案，避免 git add . 把不相關的東西加進去
git commit -m "Add unit tests for parse_date in utils"
```

**commit 訊息：**
- 先看專案歷史（`git log --oneline -20`）的慣例照著寫。有些專案用 Conventional Commits，例如 `docs: fix install steps for Windows`、`test: add tests for parse_date`
- 用英文、祈使句（Add / Fix / Update），第一行 50 字元左右

**專案要求 DCO 時**加 `-s`：`git commit -s -m "..."`，會自動加上 `Signed-off-by:` 行。忘記加的話：`git commit --amend -s --no-edit`

```bash
git push -u origin fix-issue-123
```

## 5. 送出 PR

用 GitHub 網頁開 PR，最直覺：

1. push 完後，打開自己 fork 的 GitHub 頁面（`github.com/YOU/REPO`）。上方會出現一條黃色提示，按「**Compare & pull request**」。沒看到的話，切到 Pull requests 分頁按「New pull request」。
2. 確認頁面上方的方向：**base repository** 是原專案 `OWNER/REPO` 的主線（main 或 master），**head repository** 是你的 fork 和你的 branch。
3. 填標題和描述（見下方範本），按「Create pull request」。

標題用一句話說明做了什麼，例如 `Add unit tests for parse_date`；專案有標題格式（例如 `test: ...`）就照著寫。

**一定要照專案自己的 PR 範本填。** 範本通常放在 `.github/PULL_REQUEST_TEMPLATE.md`，開 PR 時 GitHub 會自動帶進描述欄。每一欄都要填，不要刪掉範本的段落；不適用的欄位寫 N/A。

專案沒有範本時，才用這個格式：

```markdown
### Related Issues
Closes #123

### Changes
- [ ] Bug fix
- [ ] New feature
- [ ] Refactoring
- [ ] Documentation
- [ ] Test
- [ ] CI/CD pipeline
- [ ] Other

### Why
<!-- 為什麼要做這個改動？解決了什麼問題？ -->

### How
<!-- 怎麼改的？改了哪些地方？怎麼測試的？ -->

### Checklist
- [ ] Added or updated unit tests for all changes
- [ ] Added or updated documentation for all changes
```

填好的範例（補單元測試）：

```markdown
### Related Issues
Closes #123

### Changes
- [ ] Bug fix
- [ ] New feature
- [ ] Refactoring
- [ ] Documentation
- [x] Test
- [ ] CI/CD pipeline
- [ ] Other

### Why
`parse_date()` in `utils.py` currently has no test coverage.

### How
Added 6 unit tests in `tests/test_utils.py` covering valid dates, empty input,
and invalid formats. `pytest tests/test_utils.py` passes, and the full test suite passes locally.

### Checklist
- [x] Added or updated unit tests for all changes
- [ ] Added or updated documentation for all changes
```

- `Closes #123` 放在最前面，PR 合併時會自動關閉該 issue（`Fixes`、`Resolves` 也有同樣效果）
- **PR 裡不提 AI。** PR 是以你的名義送出的，內容的責任在你身上；就算有 AI 幫忙，也要自己 review、理解每一處改動，能回答維護者的問題。例外：專案的貢獻說明規定要揭露 AI 使用時，照規定寫；專案禁止 AI 產生的內容時，就不能用 AI 代寫
- 第一次貢獻可以在最後加一句 `This is my first contribution to this project, so any feedback is welcome!`，維護者通常會更有耐心
- 送出前自己先看一遍 Files changed 分頁，確認沒有不該出現的檔案（`.DS_Store`、IDE 設定、debug 用的 print）

送出後：
- 看 CI（Checks）結果，失敗就點進去看 log
- 看機器人留言：帳號名稱通常有 `[bot]` 或標著 bot，是自動產生的，不是有人在批評你。常見的有 CLA 簽署（附連結，照指示簽）、自動貼標籤、測試覆蓋率報告、「PR 太久沒動靜」的提醒

## 6. 回應 review

**先看懂 review 在說什麼。** 常見用語：

| 用語 | 意思 |
|---|---|
| LGTM | Looks good to me，看起來沒問題，通常代表同意 |
| nit / nitpick | 小細節，改不改不影響合併，但改了比較好 |
| PTAL | Please take another look，請再看一次（改完後你也可以這樣回） |
| WIP | Work in progress，還在進行中 |
| IMO / IMHO | In my (humble) opinion，我覺得 |
| AFAIK | As far as I know，據我所知 |
| ACK / NACK | 同意 / 不同意 |
| +1 / 👍 | 贊成 |
| Changes requested | review 狀態：要改完才能合併 |
| Approved | review 狀態：核准 |
| Suggested change | 維護者直接給了修改內容，可以按「Commit suggestion」直接套用 |

**回覆時：**

- 先感謝花時間 review 的人
- 逐條回應：改了就回「Done」或說明怎麼改的；不同意時有禮貌地說明理由並詢問
- 修改後直接 commit 並 push 到**同一個 branch**，PR 會自動更新：

```bash
# 改完之後
git add 檔案
git commit -m "Address review: rename helper and add edge case"
git push
```

- 不要關掉 PR 重開一個新的
- 維護者要求把多個 commit 合併成一個（squash）時：先在 PR 裡問維護者能不能在合併時用「Squash and merge」，很多專案本來就這樣做。真的需要自己合併時：

```bash
# 回到 branch 分出來的地方，保留所有改動
git reset --soft $(git merge-base HEAD upstream/main)
git commit -m "Add unit tests for parse_date"
git push --force-with-lease   # 用 --force-with-lease 而不是 --force，比較安全
```

## 7. 同步主線、解決衝突

**先試 GitHub 網頁上的按鈕**：PR 頁面出現「Update branch」時，按下去就能同步主線；簡單的衝突，可以按「Resolve conflicts」直接在網頁上處理。

網頁處理不了，或 PR 顯示「This branch has conflicts」又沒有按鈕可按時，用指令：

```bash
git fetch upstream
git rebase upstream/main
# 有衝突時，git 會停下來告訴你哪些檔案衝突
# 打開檔案，找 <<<<<<< ======= >>>>>>> 標記，保留正確的內容並刪掉標記
git add 解決好的檔案
git rebase --continue
# 全部完成後
git push --force-with-lease
```

搞砸了想重來：`git rebase --abort` 會回到 rebase 之前的狀態。

有些專案偏好用 merge 而不是 rebase（`git merge upstream/main`），看 CONTRIBUTING 或問維護者。

## 8. 常見問題

| 問題 | 解法 |
|---|---|
| 不小心在 main 上改了 | `git switch -c 新branch名`，改動會跟著帶過去 |
| commit 了不該加的檔案 | `git reset HEAD~1`（保留改動、取消最後一個 commit），重新 add |
| push 被拒絕（rejected） | 通常是 rebase 後需要 `git push --force-with-lease` |
| 想同時做第二個 PR | 從 upstream/main 再開一個新 branch，兩個 PR 互不影響 |
| fork 的 main 很舊 | GitHub fork 頁面按「Sync fork」，或 `git fetch upstream && git switch main && git merge upstream/main && git push` |
| CLA 機器人說 email 不符 | commit 的 email 要跟 GitHub 帳號綁定的 email 一致，改完 `git commit --amend --reset-author --no-edit` 再 push |
