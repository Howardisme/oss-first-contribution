[English](INSTALL.md) | 繁體中文

# 安裝

最快的安裝方式在 [README 的快速開始](README.zh-TW.md#快速開始)。這份文件是完整說明：事前準備、每個助手的安裝與更新方式、Codex 的網路設定，以及手動安裝。

## 事前準備

| 需要 | 用途 | 安裝方式 |
|---|---|---|
| Python 3.8+ | 執行分析腳本。只用標準函式庫，不需要 `pip install` | [python.org](https://www.python.org/downloads/) |
| GitHub CLI（`gh`） | 讓 GitHub API 呼叫有登入身分。沒有登入每小時只有 60 次，大約只夠評估一個專案 | macOS：`brew install gh`；Windows：`winget install --id GitHub.cli`；[其他系統](https://github.com/cli/cli#installation) |
| Claude Code、Codex 或 GitHub Copilot | 執行 skill | [Claude Code](https://code.claude.com/docs)、[Codex](https://developers.openai.com/codex)、[Copilot](https://docs.github.com/copilot) |

裝好 `gh` 之後，**重新開一個**終端機（讓它讀到新的 `PATH`），再登入：

```bash
gh auth login     # 依序選 GitHub.com → HTTPS → Login with a web browser
gh auth status    # 應該會顯示 "Logged in to github.com account 你的帳號"
```

## Claude Code Plugin

在終端機執行（需要 Claude Code 2.1.275 以上）：

```bash
claude plugin install oss-first-contribution --marketplace Howardisme/oss-first-contribution
```

開一個新的對話。聊到想參與開源時 skill 會自動啟用，也可以輸入 `/oss-first-contribution:oss-first-contribution` 直接叫出來（plugin 裡的 skill 前面會加上 plugin 名稱）。

**更新：**

```bash
claude plugin marketplace update oss-first-contribution
claude plugin update oss-first-contribution@oss-first-contribution
```

更新後要重新啟動 Claude Code 才會生效。

## Codex Plugin

```bash
codex plugin marketplace add Howardisme/oss-first-contribution
codex plugin add oss-first-contribution@oss-first-contribution
```

開啟 `codex`。skill 會自動啟用，也可以從 `/skills` 選。

**更新：**

```bash
codex plugin marketplace upgrade
codex plugin add oss-first-contribution@oss-first-contribution
```

### Codex：開啟網路

Codex 在沙盒裡執行指令，預設不開網路，但分析腳本要連到 `api.github.com`。不管是用 plugin 還是手動安裝都要處理。擇一：

- **需要時再核准。** 預設的 Auto 模式下，指令需要網路時 Codex 會先詢問，核准 `analyze_repo.py` 的指令就好。
- **一直開著。** 在 `~/.codex/config.toml` 加上：

  ```toml
  [sandbox_workspace_write]
  network_access = true
  ```

  只想這次開啟的話：`codex -c 'sandbox_workspace_write.network_access=true'`

**傳入 GitHub token。** 如果腳本說找不到 token（沙盒可能讀不到 `gh` 存的登入資訊），在啟動 Codex 前先設定環境變數：

```bash
export GITHUB_TOKEN="$(gh auth token)"     # macOS / Linux
```

```powershell
$env:GITHUB_TOKEN = (gh auth token)        # Windows（PowerShell）
```

## 手動安裝

用 GitHub Copilot，或 Claude Code、Codex 不想用 plugin 時使用。同一個助手請只用一種方式安裝（已經裝了 plugin，就不要再手動複製）。

先 clone repo，以下指令都在 repo 根目錄執行：

```bash
git clone https://github.com/Howardisme/oss-first-contribution.git
cd oss-first-contribution
```

每個助手讀取 skill 的資料夾不同：

| 助手 | 個人 skills 資料夾 |
|---|---|
| Claude Code | `~/.claude/skills/` |
| Codex | `~/.agents/skills/` |
| GitHub Copilot | `~/.copilot/skills/` 或 `~/.agents/skills/` |

**macOS / Linux**（把 `~/.claude/skills` 換成你的助手對應的資料夾）：

```bash
mkdir -p ~/.claude/skills
rm -rf ~/.claude/skills/oss-first-contribution
cp -r skills/oss-first-contribution ~/.claude/skills/
ls ~/.claude/skills/oss-first-contribution/SKILL.md     # 確認
```

**Windows（PowerShell）**（把 `.claude\skills` 換成你的助手對應的資料夾）：

```powershell
New-Item -ItemType Directory -Force "$HOME\.claude\skills" | Out-Null
Remove-Item -Recurse -Force "$HOME\.claude\skills\oss-first-contribution" -ErrorAction SilentlyContinue
Copy-Item -Recurse "skills\oss-first-contribution" "$HOME\.claude\skills\"
Test-Path "$HOME\.claude\skills\oss-first-contribution\SKILL.md"    # 確認，應該顯示 True
```

接著：

- **Claude Code：** 開啟 `claude`，輸入 `/oss-first-contribution`。如果 `~/.claude/skills` 是在 Claude Code 開著的時候才建立的，先執行一次 `/reload-skills`。
- **Codex：** 開啟 `codex`，輸入 `$oss-first-contribution` 或從 `/skills` 選。記得[開啟網路](#codex開啟網路)。
- **GitHub Copilot：** 在 VS Code 打開 Copilot Chat，切到 **Agent** 模式，輸入 `/oss-first-contribution`。Copilot 執行終端機指令前會先詢問，看到 `analyze_repo.py` 的指令時按允許。看不到 skill 的話，先重新載入視窗（**Developer: Reload Window**），再到 **Chat: Open Customizations → Skills** 確認。

**更新：** 執行 `git pull` 再跑一次上面的複製指令。指令會先刪掉舊的資料夾，上游刪除的檔案不會殘留。
