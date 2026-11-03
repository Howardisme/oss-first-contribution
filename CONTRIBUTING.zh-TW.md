[English](CONTRIBUTING.md) | 繁體中文

# 貢獻指南

歡迎所有形式的貢獻：分享經驗、分享知識、回報問題、改善文件或程式，都屬於開源貢獻的範疇。

## 可以怎麼貢獻

| 類型 | 怎麼做 |
|---|---|
| 分享經驗 | 在 [`experiences/`](experiences/) 新增一篇分享，送 PR（見下方） |
| 回報問題 | 用 *Bug report* issue 範本，附上對話片段或腳本輸出 |
| 提出功能 | 用 *Feature request* issue 範本，先討論再動手 |
| 改 skill、文件、腳本 | 直接送 PR；比較大的改動，先開 issue 討論 |

### 分享經驗

完成（或卡在）一次開源貢獻之後，把經驗寫下來，給之後的同學參考。PR 有沒有被合併都可以分享，卡住的過程往往最有參考價值。

複製 [`experiences/_template.zh-TW.md`](experiences/_template.zh-TW.md)（英文版是 [`_template.md`](experiences/_template.md)），存成 `experiences/你的GitHub帳號-sharing01.md`（之後再分享就用 `02`、`03`），填好後送 PR。不熟 git 也沒關係：在 GitHub 網頁打開 `experiences/` 資料夾，按 **Add file → Create new file**，就能直接寫、直接送出 PR。

## 送 PR

- issue、PR 說明和 review 回覆都用英文寫，跟參與國際大型專案時一樣
- 照 PR 範本填寫，不適用的欄位寫 N/A
- **新增或修改 `scripts/` 裡的程式時，要補上 unit test，並跑過測試：**

  ```bash
  python -m unittest discover -s tests
  ```

  測試不能連網路，需要的假資料請加在 `tests/test_analyze_repo.py` 的 `FakeGitHub`。

## 專案結構

```
.
├── skills/oss-first-contribution/   # skill 本體，安裝的就是這個資料夾
│   ├── SKILL.md                     # 給助手的主要說明（七個階段）
│   ├── config.json                  # 指標、權重、門檻、標籤的預設值
│   ├── references/                  # 某個階段需要時才讀的參考資料
│   └── scripts/analyze_repo.py      # 呼叫 GitHub API 的分析腳本（quick / health / opportunities / claims）
├── .claude-plugin/                  # Claude Code 的 plugin 與 marketplace 設定
├── .codex-plugin/                   # Codex 的 plugin 設定
├── .agents/plugins/                 # Codex 的 marketplace 設定
├── experiences/                     # 同學的開源經驗分享
├── tests/                           # 用假 GitHub API 的離線測試
└── .github/                         # PR、Issue 範本與 CI
```

## 開發

先在 GitHub 上 fork 這個 repo，再 clone 你的 fork，跑一次測試確認環境正常：

```bash
git clone https://github.com/你的帳號/oss-first-contribution.git
cd oss-first-contribution
python -m unittest discover -s tests -v
```

測試完全不連網路：所有 API 呼叫都會導到 [`tests/test_analyze_repo.py`](tests/test_analyze_repo.py) 裡的 `FakeGitHub`。CI 會在 Python 3.8 和 3.12 上執行。

## 修改 skill 時

- 同一條規則可能寫在好幾個檔案裡（`SKILL.md`、`references/`、`config.json`），改的時候一起改
- 這份 skill 同時給 Claude、Codex、GitHub Copilot 使用：不要寫只有某一家才有的工具名稱，也不要改 `name` 或資料夾名稱

## 關於 AI

可以用 AI 幫忙，但 PR 是以你的名義送出的：送出的每一行都要自己看過、能解釋。

## 互相尊重

這是開源社群裡最重要的一件事。

