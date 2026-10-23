#!/usr/bin/env python3
"""開源專案新手適合度分析 / Beginner-friendliness check for a GitHub repo.

Usage:
  python analyze_repo.py quick OWNER/REPO [OWNER/REPO ...] [--json]
  python analyze_repo.py health OWNER/REPO [OWNER/REPO ...] [--config student.json] [--json]
  python analyze_repo.py opportunities OWNER/REPO [--config my.json] [--limit 8] [--json]
  python analyze_repo.py claims OWNER/REPO ISSUE [ISSUE ...] [--json]

  quick          階段 1：GitHub 連結、簡介、語言、star 數、有沒有貢獻說明（CONTRIBUTING 或 README 段落；每個專案 2–3 次 API）
  health         階段 2：基礎資訊（不計分）＋客觀指標評分（活躍度、外部貢獻者友善、維護者回應、
                 新手入口、維護者永續性）＋主觀指標欄位（由 AI 助手填）
  opportunities  階段 3：新手 issue、文件/翻譯/測試 issue、缺少的翻譯語系、沒有測試的檔案
  claims         階段 3：推薦前檢查 issue 有沒有人在做（口頭認領、提到它的 PR；每個 issue 2–3 次 API）

Auth: 設定 GITHUB_TOKEN（或 GH_TOKEN），或先 `gh auth login`。
沒有 token 時 GitHub 每小時只給 60 次請求，一次 health 大約用 50 次。

Only the Python standard library is used.
"""

import argparse
import base64
import json
import os
import re
import statistics
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, deque
from datetime import datetime, timedelta, timezone
from pathlib import Path

API = "https://api.github.com"
DEFAULT_CONFIG = Path(__file__).resolve().parent.parent / "config.json"
NOW = datetime.now(timezone.utc)
OUTSIDE_ASSOCIATIONS = {"CONTRIBUTOR", "FIRST_TIME_CONTRIBUTOR", "FIRST_TIMER", "NONE"}


# ---------------------------------------------------------------- GitHub access

class GitHubError(Exception):
    pass


def find_token():
    for key in ("GITHUB_TOKEN", "GH_TOKEN"):
        if os.environ.get(key):
            return os.environ[key]
    try:
        out = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, timeout=10)
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        pass
    return None


class GitHub:
    def __init__(self, token=None):
        self.token = token
        self.calls = 0
        # Search API: 10/min without a token, 30/min with one.
        self._search_limit = 28 if token else 9
        self._search_times = deque()

    def get(self, path, params=None):
        url = path if path.startswith("http") else API + path
        if params:
            url += ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "oss-first-contribution-skill",
        })
        if self.token:
            req.add_header("Authorization", f"Bearer {self.token}")
        self.calls += 1
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                headers = {k.lower(): v for k, v in resp.headers.items()}
                return json.load(resp), headers
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")[:300]
            if e.code in (403, 429) and "rate limit" in body.lower():
                hint = "" if self.token else "設定 GITHUB_TOKEN 或執行 `gh auth login` 後再試（有 token 每小時 5000 次）。"
                raise GitHubError(f"GitHub API 額度用完了。{hint}") from None
            if e.code == 404:
                raise GitHubError(f"找不到 {path}（專案名稱打錯，或是私有專案？）") from None
            raise GitHubError(f"GitHub API 錯誤 {e.code}：{body}") from None
        except urllib.error.URLError as e:
            raise GitHubError(f"連不到 GitHub API：{e.reason}。如果是在 Codex 等預設不開網路的沙盒裡執行，"
                              "請核准這個指令使用網路，或在設定裡開啟網路存取。") from None

    def search(self, query, **params):
        self._throttle_search()
        data, _ = self.get("/search/issues", {"q": query, **params})
        return data

    def _throttle_search(self):
        window = 61
        now = time.monotonic()
        while self._search_times and now - self._search_times[0] > window:
            self._search_times.popleft()
        if len(self._search_times) >= self._search_limit:
            wait = window - (now - self._search_times[0])
            print(f"（搜尋 API 有速率限制，等待 {wait:.0f} 秒…）", file=sys.stderr)
            time.sleep(max(wait, 0))
            self._search_times.popleft()
        self._search_times.append(time.monotonic())


# ---------------------------------------------------------------- helpers

def parse_ts(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def days_between(start, end=None):
    return ((end or NOW) - start).total_seconds() / 86400


def iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


# Accounts that post automatically but GitHub does not flag as bots (many are plain user accounts).
KNOWN_BOT_LOGINS = {
    "codecov-commenter", "codecov", "coveralls", "claassistant", "cla-bot", "cla-assistant", "github-actions",
    "coderabbitai", "copilot", "copilot-pull-request-reviewer", "copilot-swe-agent", "sonarcloud",
    "sonarqubecloud", "vercel", "netlify", "pre-commit-ci", "allcontributors", "stale", "mergify", "dosubot",
    "sourcery-ai", "gemini-code-assist", "greptile-apps", "deepsource-io", "codspeed-hq", "changeset-bot",
    "socket-security", "linear", "kodiakhq", "renovate", "dependabot", "welcome", "imgbot", "snyk-bot",
}
BOT_LOGIN_RE = re.compile(r"(\[bot\]|-bot|_bot|-ci|-commenter|-assistant)$|^bot-", re.I)


def is_bot(user):
    if not user:
        return True
    login = (user.get("login") or "").lower()
    return user.get("type") == "Bot" or login in KNOWN_BOT_LOGINS or bool(BOT_LOGIN_RE.search(login))


def count_via_link(gh, path, params):
    """Count list items cheaply: ask for 1 per page and read the last page number."""
    data, headers = gh.get(path, {**params, "per_page": 1})
    m = re.search(r'[?&]page=(\d+)[^>]*>;\s*rel="last"', headers.get("link", ""))
    return int(m.group(1)) if m else len(data)


def normalize_repo(text):
    text = text.strip().rstrip("/")
    text = re.sub(r"^(https?://)?(www\.)?github\.com/", "", text)
    text = re.sub(r"\.git$", "", text)
    parts = text.split("/")
    if len(parts) < 2 or not parts[0] or not parts[1]:
        raise SystemExit(f"看不懂的專案名稱：{text}（請用 OWNER/REPO 或 GitHub 網址）")
    return f"{parts[0]}/{parts[1]}"


def deep_merge(base, override):
    out = dict(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_config(path):
    cfg = json.loads(DEFAULT_CONFIG.read_text(encoding="utf-8"))
    if path:
        cfg = deep_merge(cfg, json.loads(Path(path).read_text(encoding="utf-8")))
    return cfg


def norm_label(s):
    s = s.lower().replace("_", " ")
    s = re.sub(r"[^\w\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def get_labels(gh, repo):
    labels, page = [], 1
    while page <= 3:
        data, _ = gh.get(f"/repos/{repo}/labels", {"per_page": 100, "page": page})
        labels += [l["name"] for l in data]
        if len(data) < 100:
            break
        page += 1
    return labels


def match_labels(labels, patterns):
    pats = [norm_label(p) for p in patterns]
    matched = []
    for name in labels:
        n = norm_label(name)
        if any(re.search(rf"(^|\s){re.escape(p)}(\s|$)", n) for p in pats):
            matched.append(name)
    return matched


def find_issues_with_labels(gh, repo, label_names, per_label):
    """Open, unassigned issues with no linked PR, carrying any of the labels."""
    found = {}
    for name in label_names[:4]:
        q = f'repo:{repo} is:issue is:open no:assignee -linked:pr label:"{name}"'
        data = gh.search(q, sort="created", order="desc", per_page=per_label)
        for it in data.get("items", []):
            entry = found.setdefault(it["number"], {
                "number": it["number"],
                "title": it["title"],
                "url": it["html_url"],
                "labels": [l["name"] for l in it.get("labels", [])],
                "comments": it.get("comments", 0),
                "age_days": round(days_between(parse_ts(it["created_at"]))),
                "updated_days_ago": round(days_between(parse_ts(it["updated_at"]))),
            })
            entry.setdefault("matched", set()).add(name)
    items = sorted(found.values(), key=lambda x: x["age_days"])  # newest first
    for it in items:
        it["matched"] = sorted(it["matched"])
    return items


# ---------------------------------------------------------------- health

INTERNAL_ASSOCIATIONS = {"OWNER", "MEMBER", "COLLABORATOR"}

METRIC_INFO = {
    # name: (group, 中文名稱, 代表什麼)
    "days_since_last_commit": ("活躍度", "距離上次 commit（天）", "專案還有沒有人在動"),
    "commits_in_window": ("活躍度", "近期 commit 數", "開發活躍程度"),
    "merged_prs_in_window": ("活躍度", "近期合併的 PR 數", "PR 有沒有在被處理"),
    "outside_pr_merge_rate": ("對外部貢獻者友善", "外部 PR 合併率", "非核心成員送 PR 被接受的比例"),
    "median_days_to_merge": ("對外部貢獻者友善", "外部 PR 合併中位天數", "外部 PR 送出後大約多久會被合併"),
    "outside_pr_first_response_days": ("對外部貢獻者友善", "外部 PR 首次回應中位天數", "送出 PR 後多久會有維護者真人回覆"),
    "issue_response_rate": ("維護者回應", "Issue 回應率", "開 issue 後有沒有人理"),
    "median_days_first_response": ("維護者回應", "Issue 首次回應中位天數", "多快會有人回"),
    "issue_close_ratio": ("維護者回應", "Issue 關閉/新增比", "問題有沒有在被消化"),
    "open_newcomer_issues": ("新手入口", "可認領的新手 issue 數", "現在有沒有現成的新手題目"),
    "bus_factor": ("維護者永續性", "Bus factor", "最少幾個人就貢獻了一半的 commit"),
    "active_maintainers": ("維護者永續性", "核心成員人數", "近期有在動的維護者與常態 commit 者"),
}
BASIC_ZH = {"stars": "⭐ Star", "forks": "Fork", "open_issues": "Open issues", "open_prs": "Open PRs",
            "contributors": "貢獻者", "language": "語言", "license": "授權", "created": "建立於", "topics": "主題"}
VERDICT_ZH = {"recommended": "✅ 適合新手", "caution": "⚠️ 可以，但要注意", "not_recommended": "❌ 不建議當第一個專案"}


def score_metric(value, spec):
    if value is None:
        return None
    good, bad = spec["good"], spec["bad"]
    if good == bad:
        return 100 if value == good else 0
    t = (value - bad) / (good - bad)
    return round(max(0.0, min(1.0, t)) * 100)


def activity_tier(days, tiers):
    for t in tiers:
        if t.get("max_days") is None or days <= t["max_days"]:
            return t
    return tiers[-1]


def fetch_file_text(gh, api_url):
    try:
        data, _ = gh.get(api_url)
        return base64.b64decode(data.get("content", "")).decode("utf-8", errors="replace")
    except (GitHubError, ValueError):
        return ""


MD_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
HTML_HEADING_RE = re.compile(r"^\s*<h([1-6])[^>]*>(.*?)</h\1>", re.I)
# "Contributing", "How to contribute", "Contributions welcome", "貢獻"; not "Contributors" (a list of people).
CONTRIB_TITLE_RE = re.compile(r"contributing|contribute|contribution|how to help|貢獻", re.I)


def heading_of(lines, i):
    """(level, title) if line i is a Markdown, setext or HTML heading, else None."""
    line = lines[i]
    m = MD_HEADING_RE.match(line)
    if m:
        return len(m.group(1)), m.group(2)
    h = HTML_HEADING_RE.match(line)
    if h:
        return int(h.group(1)), re.sub(r"<[^>]+>", "", h.group(2))
    if line.strip() and i + 1 < len(lines) and re.match(r"^(=+|-+)\s*$", lines[i + 1]):
        return (1 if lines[i + 1].startswith("=") else 2), line.strip()
    return None


def contributing_section(text):
    """The README's Contributing section (heading + body), or None."""
    lines = text.splitlines()
    for i in range(len(lines)):
        h = heading_of(lines, i)
        if not h or not CONTRIB_TITLE_RE.search(h[1]):
            continue
        level, body = h[0], [lines[i]]
        for j in range(i + 1, len(lines)):
            nxt = heading_of(lines, j)
            if nxt and nxt[0] <= level:
                break
            body.append(lines[j])
        return "\n".join(body).strip()[:5000]
    return None


def readme_contributing(gh, repo):
    """Look for a Contributing section in the README. 1 API call."""
    try:
        data, _ = gh.get(f"/repos/{repo}/readme")
        text = base64.b64decode(data.get("content", "")).decode("utf-8", errors="replace")
    except (GitHubError, ValueError):
        return None
    section = contributing_section(text)
    return {"text": section, "url": data.get("html_url")} if section else None


def find_contributing(gh, repo):
    """Contribution guide: a CONTRIBUTING file, or else a Contributing section in the README.

    Returns {"source": "file" | "readme" | None, "url": ..., "text": ...}; source None = no guide found,
    and the whole result is None when GitHub could not be asked.
    """
    try:
        prof, _ = gh.get(f"/repos/{repo}/community/profile")
    except GitHubError:
        return None
    c = (prof.get("files") or {}).get("contributing")
    if c:
        return {"source": "file", "url": c.get("html_url"), "api_url": c.get("url")}
    r = readme_contributing(gh, repo)
    if r:
        return {"source": "readme", "url": r["url"], "text": r["text"]}
    return {"source": None, "url": None}


# Phrases that mean "outside PRs need permission first" or "this is mostly an internal project".
GATE_RE = re.compile(
    r"closed automatically|automatically closed|auto-?clos|will be closed"
    r"|must (first )?be (assigned|approved|accepted|triaged)|label(ed|s)? .{0,10}accepted"
    r"|(approved|accepted|assigned) issue|open an issue (first|before)|discuss .{0,40}before"
    r"|before (opening|submitting|sending) a (pr|pull request)"
    r"|internal use|internal team|(not|no longer|do not|don't) accept|only accept|by invitation|maintainers only",
    re.I)


def scan_rules(text):
    """Look for CLA / DCO / AI policy / contribution barriers in contribution guidelines."""
    flags = {"cla": False, "dco": False, "ai_policy_lines": [], "gate_lines": []}
    if not text:
        return flags
    flags["cla"] = bool(re.search(r"\bCLA\b|contributor license agreement", text, re.I))
    flags["dco"] = bool(re.search(r"\bDCO\b|signed-off-by|developer certificate of origin", text, re.I))
    ai_re = re.compile(r"\b(AI|LLMs?|ChatGPT|Copilot|Claude|Gemini)\b|generative|machine[- ]generated|AI[- ]generated|AI[- ]assisted", re.I)
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if ai_re.search(line) and len(flags["ai_policy_lines"]) < 4:
            flags["ai_policy_lines"].append(line[:200])
        if GATE_RE.search(line) and len(flags["gate_lines"]) < 4:
            flags["gate_lines"].append(line[:200])
    return flags


def collect_basic(gh, repo, info, fields):
    b = {}
    open_prs = None
    if "open_prs" in fields or "open_issues" in fields:
        open_prs = gh.search(f"repo:{repo} is:pr is:open", per_page=1)["total_count"]
    for f in fields:
        if f == "stars":
            b[f] = info.get("stargazers_count")
        elif f == "forks":
            b[f] = info.get("forks_count")
        elif f == "open_prs":
            b[f] = open_prs
        elif f == "open_issues":
            # GitHub's open_issues_count includes open PRs.
            b[f] = max(info.get("open_issues_count", 0) - (open_prs or 0), 0) if info.get("has_issues", True) else None
        elif f == "contributors":
            try:
                b[f] = count_via_link(gh, f"/repos/{repo}/contributors", {"anon": "true"})
            except GitHubError:
                b[f] = None  # very large repos refuse this endpoint
        elif f == "language":
            b[f] = info.get("language")
        elif f == "license":
            b[f] = (info.get("license") or {}).get("spdx_id")
        elif f == "created":
            b[f] = (info.get("created_at") or "")[:10] or None
        elif f == "topics":
            b[f] = ", ".join(info.get("topics", [])[:5]) or None
        else:
            b[f] = None
    return b


def first_response(events, created, also_at=None):
    """Days until the first event (e.g. a maintainer comment, or merging). None if nothing happened yet."""
    times = list(events)
    if also_at:
        times.append(parse_ts(also_at))
    return days_between(created, min(times)) if times else None


VERDICT_ORDER = ["not_recommended", "caution", "recommended"]


def collect_health(gh, repo, cfg):
    aw, rw, sw = cfg["activity_window_days"], cfg["ratio_window_days"], cfg["sustainability_window_days"]
    smp = cfg["samples"]
    KNOWN_BOT_LOGINS.update(l.lower() for l in cfg.get("bot_logins", []))
    calls_before = gh.calls
    m, facts, notes = {}, {}, []
    sustain_since = NOW - timedelta(days=sw)
    maintainers = set()  # seen as OWNER / MEMBER / COLLABORATOR

    info, _ = gh.get(f"/repos/{repo}")
    facts.update({
        "full_name": info["full_name"], "url": info["html_url"], "description": info.get("description"),
        "archived": info.get("archived", False), "has_issues": info.get("has_issues", True),
    })
    basic = collect_basic(gh, repo, info, cfg["basic"])

    # --- Activity
    commits, _ = gh.get(f"/repos/{repo}/commits", {"per_page": 1})
    m["days_since_last_commit"] = (
        round(days_between(parse_ts(commits[0]["commit"]["committer"]["date"])), 1) if commits else None)
    aw_since = NOW - timedelta(days=aw)
    m["commits_in_window"] = count_via_link(gh, f"/repos/{repo}/commits", {"since": iso(aw_since)})
    m["merged_prs_in_window"] = gh.search(
        f"repo:{repo} is:pr is:merged merged:>={aw_since.date().isoformat()}", per_page=1)["total_count"]

    # --- Who commits: bus factor, and the core team.
    # Done first because employees with private org membership show up as plain CONTRIBUTORs;
    # frequent committers are treated as core so their PRs don't count as "outside".
    counts = Counter()
    logins = set()  # commit authors linked to a GitHub account (others are just names)
    truncated = True
    for page in range(1, smp["commit_pages"] + 1):
        data, _ = gh.get(f"/repos/{repo}/commits", {"since": iso(sustain_since), "per_page": 100, "page": page})
        for c in data:
            author = c.get("author")
            if author:
                if is_bot(author):
                    continue
                key = author["login"]
                logins.add(key)
            else:
                key = ((c.get("commit") or {}).get("author") or {}).get("name") or "unknown"
                if key.lower().endswith("[bot]"):
                    continue
            counts[key] += 1
        if len(data) < 100:
            truncated = False
            break
    total = sum(counts.values())
    facts["committers_in_window"] = len(counts)
    if total:
        acc = bf = 0
        for _, n in counts.most_common():
            acc, bf = acc + n, bf + 1
            if acc * 2 >= total:
                break
        m["bus_factor"] = bf
        facts["top_committer_share"] = round(counts.most_common(1)[0][1] / total, 2)
    else:
        m["bus_factor"] = 0
        facts["top_committer_share"] = None
        notes.append(f"最近 {sw} 天沒有 commit，bus factor 記為 0。")
    if truncated:
        notes.append(f"commit 太多，bus factor 和核心成員只用最近 {smp['commit_pages'] * 100} 筆計算。")
    frequent = {k for k, n in counts.items() if n >= cfg["core_min_commits"] and k in logins}
    owner = info.get("owner") or {}
    if owner.get("type") == "User" and owner.get("login") in counts:
        maintainers.add(owner["login"])  # solo projects: the owner often commits directly

    def is_core(user, assoc=None):
        login = (user or {}).get("login")
        return assoc in INTERNAL_ASSOCIATIONS or login in frequent or login in maintainers

    def note_maintainer(obj, when):
        user = obj.get("user") or {}
        if obj.get("author_association") in INTERNAL_ASSOCIATIONS and not is_bot(user) \
                and when and parse_ts(when) >= sustain_since:
            maintainers.add(user["login"])

    def is_outside(obj):
        user = obj.get("user")
        return (not is_bot(user) and obj.get("author_association") in OUTSIDE_ASSOCIATIONS
                and not is_core(user, obj.get("author_association")))

    def maintainer_reply(obj, author):
        """A human from the core team, other than the author. Bots and other users don't count."""
        user = obj.get("user") or {}
        return not is_bot(user) and user.get("login") != author and is_core(user, obj.get("author_association"))

    # --- Outside contributors: merge rate and merge speed (most recent samples, no time limit)
    closed, _ = gh.get(f"/repos/{repo}/pulls", {"state": "closed", "sort": "updated", "direction": "desc", "per_page": 100})
    closed = sorted((p for p in closed if p.get("closed_at") and not is_bot(p.get("user"))),
                    key=lambda p: p["closed_at"], reverse=True)
    for p in closed:
        note_maintainer(p, p["closed_at"])
    outside = [p for p in closed if is_outside(p)][: smp["outside_prs"]]
    merged_outside = [p for p in outside if p.get("merged_at")]
    facts["outside_prs_sampled"], facts["outside_prs_merged"] = len(outside), len(merged_outside)
    facts["outside_merged_authors"] = Counter(p["user"]["login"] for p in merged_outside).most_common(5)
    if len(outside) >= 3:
        m["outside_pr_merge_rate"] = round(len(merged_outside) / len(outside), 2)
    else:
        m["outside_pr_merge_rate"] = None
        notes.append("最近關閉的 PR 中，外部貢獻者的 PR 少於 3 個，合併率不列入計分。")
    if len(merged_outside) >= 3:
        m["median_days_to_merge"] = round(statistics.median(
            days_between(parse_ts(p["created_at"]), parse_ts(p["merged_at"])) for p in merged_outside), 1)
    else:
        m["median_days_to_merge"] = None
        notes.append("被合併的外部 PR 少於 3 個，合併速度不列入計分。")

    # --- Outside contributors: first human maintainer response on their PRs (closing doesn't count)
    recent, _ = gh.get(f"/repos/{repo}/pulls", {"state": "all", "sort": "created", "direction": "desc", "per_page": 50})
    for p in recent:
        note_maintainer(p, p["created_at"])
    cands = [p for p in recent if is_outside(p) and days_between(parse_ts(p["created_at"])) >= 2][: smp["pr_response"]]
    waits, unanswered = [], 0
    for p in cands:
        created, author = parse_ts(p["created_at"]), p["user"]["login"]
        events = []
        comments, _ = gh.get(f"/repos/{repo}/issues/{p['number']}/comments", {"per_page": 30})
        for c in comments:
            note_maintainer(c, c["created_at"])
            if maintainer_reply(c, author):
                events.append(parse_ts(c["created_at"]))
        reviews, _ = gh.get(f"/repos/{repo}/pulls/{p['number']}/reviews", {"per_page": 30})
        for r in reviews:
            if r.get("submitted_at") and maintainer_reply(r, author):
                events.append(parse_ts(r["submitted_at"]))
        wait = first_response(events, created, p.get("merged_at"))  # merging is a maintainer action
        if wait is None:
            # No human maintainer ever replied (including PRs a bot closed): count the time so far.
            unanswered += 1
            wait = days_between(created)
        waits.append(wait)
    facts["pr_response_sampled"], facts["pr_response_unanswered"] = len(cands), unanswered
    if len(cands) >= 3:
        m["outside_pr_first_response_days"] = round(statistics.median(waits), 1)
    else:
        m["outside_pr_first_response_days"] = None
        notes.append("外部貢獻者的 PR 太少（少於 3 個），PR 首次回應時間不列入計分。")

    # --- Maintainer responsiveness on issues opened by outsiders
    m["issue_response_rate"] = m["median_days_first_response"] = m["issue_close_ratio"] = None
    if facts["has_issues"]:
        rw_since = (NOW - timedelta(days=rw)).date().isoformat()
        opened = gh.search(f"repo:{repo} is:issue created:>={rw_since}", per_page=1)["total_count"]
        closed_n = gh.search(f"repo:{repo} is:issue is:closed closed:>={rw_since}", per_page=1)["total_count"]
        m["issue_close_ratio"] = round(closed_n / opened, 2) if opened else None
        if not opened:
            notes.append(f"最近 {rw} 天沒有新 issue。")
        issues, _ = gh.get(f"/repos/{repo}/issues", {"state": "all", "sort": "created", "direction": "desc", "per_page": 50})
        sample = [i for i in issues if "pull_request" not in i and is_outside(i)
                  and days_between(parse_ts(i["created_at"])) >= 2][: smp["issues"]]
        times, unanswered_i = [], 0
        for i in sample:
            events = []
            if i.get("comments", 0) > 0:
                comments, _ = gh.get(f"/repos/{repo}/issues/{i['number']}/comments", {"per_page": 10})
                for c in comments:
                    note_maintainer(c, c["created_at"])
                    if maintainer_reply(c, i["user"]["login"]):
                        events.append(parse_ts(c["created_at"]))
            wait = first_response(events, parse_ts(i["created_at"]))
            if wait is None:
                unanswered_i += 1
            else:
                times.append(wait)
        facts["issues_sampled"], facts["issues_unanswered"] = len(sample), unanswered_i
        if sample:
            m["issue_response_rate"] = round(len(times) / len(sample), 2)
            m["median_days_first_response"] = round(statistics.median(times), 1) if times else None
        else:
            notes.append("最近沒有外部使用者開的 issue，issue 回應指標不列入計分。")
    else:
        notes.append("這個專案關閉了 GitHub Issues，可能用其他地方追蹤（看 README / CONTRIBUTING）。")

    # --- Newcomer entry points
    labels = get_labels(gh, repo)
    newbie = match_labels(labels, cfg["newcomer_labels"])
    facts["newcomer_labels_found"] = newbie
    m["open_newcomer_issues"] = len(find_issues_with_labels(gh, repo, newbie, 100)) if newbie else 0
    if not newbie:
        notes.append("專案沒有新手標籤（如 good first issue），不代表不歡迎新手，但要自己找題目。")

    # --- Contribution rules (not scored; the guide itself was checked in stage 1)
    guide = find_contributing(gh, repo)
    facts["contributing_source"] = guide["source"] if guide else None
    facts["contributing_url"] = guide["url"] if guide else None
    if guide and guide["source"] == "file":
        facts["contributing_flags"] = scan_rules(fetch_file_text(gh, guide["api_url"]))
    elif guide and guide["source"] == "readme":
        facts["contributing_flags"] = scan_rules(guide["text"])
    else:
        facts["contributing_flags"] = scan_rules("")

    core = maintainers | frequent
    m["active_maintainers"] = len(core)
    facts["core_team"] = sorted(core, key=lambda k: -counts.get(k, 0))

    # --- Score
    rows, total_score, weight_sum = [], 0.0, 0.0
    activity_label = None
    for name, spec in cfg["metrics"].items():
        w = spec.get("weight", 0)
        value = m.get(name)
        if name == "days_since_last_commit":
            tier = activity_tier(value, cfg["activity_tiers"]) if value is not None else None
            sc = tier["score"] if tier else None
            activity_label = tier["label"] if tier else None
        else:
            sc = score_metric(value, spec)
        group, zh, meaning = METRIC_INFO.get(name, ("其他", name, ""))
        rows.append({"metric": name, "group": group, "name_zh": zh, "meaning": meaning,
                     "value": value, "score": sc, "weight": w})
        if sc is not None and w:
            total_score += sc * w
            weight_sum += w
    overall = round(total_score / weight_sum) if weight_sum else None
    full_weight = sum(s.get("weight", 0) for s in cfg["metrics"].values())
    coverage = round(weight_sum / full_weight, 2) if full_weight else 0
    if coverage < 0.6:
        notes.append(f"只有 {int(coverage * 100)}% 的權重有資料，分數參考性較低。")

    th, db = cfg["verdict_thresholds"], cfg["dealbreakers"]
    blockers = []
    if db.get("archived") and facts["archived"]:
        blockers.append("專案已封存（archived），不會再接受 PR。")
    limit = db.get("max_days_since_last_commit")
    if limit and m["days_since_last_commit"] is not None and m["days_since_last_commit"] > limit:
        blockers.append(f"超過 {limit} 天沒有 commit。")
    if blockers or overall is None:
        verdict = "not_recommended"
    elif overall >= th["recommended"]:
        verdict = "recommended"
    elif overall >= th["caution"]:
        verdict = "caution"
    else:
        verdict = "not_recommended"

    # A high total can't hide a project that rarely accepts or answers outsiders.
    caps = []
    for name, cap in cfg.get("verdict_caps", {}).items():
        value = m.get(name)
        if value is None or value >= cap["below"]:
            continue
        if VERDICT_ORDER.index(verdict) > VERDICT_ORDER.index(cap["max_verdict"]):
            verdict = cap["max_verdict"]
        caps.append(f"{METRIC_INFO.get(name, ('', name, ''))[1]}只有 {fmt_value(name, value)}，"
                    f"低於 {fmt_value(name, cap['below'])}，結論最多到「{VERDICT_ZH[cap['max_verdict']]}」")

    return {"repo": repo, "basic": basic, "overall_score": overall, "verdict": verdict, "caps": caps,
            "activity_label": activity_label, "blockers": blockers, "score_coverage": coverage,
            "metrics": rows, "subjective": cfg.get("subjective", []),
            "facts": facts, "notes": notes, "api_calls": gh.calls - calls_before}


def fmt_value(name, v):
    if v is None:
        return "—"
    if name in ("outside_pr_merge_rate", "issue_response_rate"):
        return f"{v * 100:.0f}%"
    return f"{v:g}"


def fmt_basic(v):
    if v is None:
        return "—"
    if isinstance(v, int) and v >= 10000:
        return f"{v / 1000:.1f}k"
    return str(v)


def print_health(results, cfg):
    print("# 專案評估\n")
    print("> 「助手評語」「助手評分」「助手綜合評分」由 AI 助手讀過專案後填寫；腳本只負責數字。\n")
    fields = cfg["basic"]
    if fields:
        print("## 基礎資訊（不計分）\n")
        print("| 專案 | " + " | ".join(BASIC_ZH.get(f, f) for f in fields) + " |")
        print("|---" * (len(fields) + 1) + "|")
        for r in results:
            if "error" in r:
                print(f"| {r['repo']} | ⚠️ {r['error']} |" + " |" * (len(fields) - 1))
                continue
            cells = [f"[{r['repo']}]({r['facts']['url']})"] + [fmt_basic(r["basic"].get(f)) for f in fields]
            print("| " + " | ".join(cells) + " |")
        print()
    for r in results:
        if "error" not in r:
            print_one_health(r)


def print_one_health(r):
    f = r["facts"]
    print(f"## {r['repo']}\n")
    if f.get("description"):
        print(f"{f['description']}\n")
    score = "—" if r["overall_score"] is None else r["overall_score"]
    act = f"｜活躍程度：{r['activity_label']}" if r["activity_label"] else ""
    print(f"**腳本總分 {score}/100 → {VERDICT_ZH[r['verdict']]}**{act}（資料涵蓋 {int(r['score_coverage'] * 100)}% 權重）\n")
    for b in r["blockers"]:
        print(f"- 🚫 {b}")
    for c in r.get("caps", []):
        print(f"- ⚠️ {c}")
    print("\n### 客觀指標\n")
    print("| 面向 | 指標 | 數值 | 分數 | 權重 | 助手評語 |\n|---|---|---|---|---|---|")
    last_group = None
    for row in r["metrics"]:
        if not row["weight"]:
            continue
        group = row["group"] if row["group"] != last_group else ""
        last_group = row["group"]
        sc = "—" if row["score"] is None else row["score"]
        print(f"| {group} | {row['name_zh']} | {fmt_value(row['metric'], row['value'])} | {sc} | {row['weight']} |  |")
    extra = []
    if f.get("top_committer_share") is not None:
        extra.append(f"最大貢獻者佔近期 commit 的 {f['top_committer_share'] * 100:.0f}%")
    if f.get("core_team"):
        extra.append(f"核心成員（推測）：{', '.join(f['core_team'][:8])}")
    if f.get("outside_merged_authors"):
        authors = ", ".join(f"{a}（{n}）" for a, n in f["outside_merged_authors"])
        extra.append(f"被合併的外部 PR 作者：{authors}")
    if f.get("pr_response_unanswered"):
        extra.append(f"抽樣的 {f['pr_response_sampled']} 個外部 PR 中，有 {f['pr_response_unanswered']} 個沒有維護者真人回覆")
    if extra:
        print("\n**用來核對數字的資訊**（數字看起來好到可疑時，先打開幾個 PR 確認）")
        for x in extra:
            print(f"- {x}")
    if r["subjective"]:
        print("\n### 主觀指標（助手評分 1–5，需附證據）\n")
        print("| 指標 | 怎麼判斷 | 重要程度 | 助手評分 | 證據 |\n|---|---|---|---|---|")
        for s in r["subjective"]:
            print(f"| {s.get('name', '')} | {s.get('how', '')} | {s.get('importance', '')} |  |  |")
    print("\n**助手綜合評分（1–5）：**  \n")
    cf = f.get("contributing_flags", {})
    reminders = []
    src = f.get("contributing_source")
    if src == "readme":
        reminders.append("沒有 CONTRIBUTING 檔案，貢獻說明寫在 README 的段落裡")
    elif src is None:
        reminders.append("找不到貢獻說明（CONTRIBUTING 或 README 段落），請手動確認")
    if cf.get("cla"):
        reminders.append("需要簽 CLA（貢獻者授權協議），第一次送 PR 時會被要求簽署")
    if cf.get("dco"):
        reminders.append("需要 DCO sign-off：commit 要加 `-s`（`git commit -s`）")
    if cf.get("gate_lines"):
        reminders.append("⚠️ 貢獻說明裡有門檻或限制，新手請先讀懂再動手。相關段落：\n" +
                         "\n".join(f"  > {line}" for line in cf["gate_lines"]))
    if cf.get("ai_policy_lines"):
        reminders.append("貢獻說明提到 AI，請讀完整規定。相關段落：\n" +
                         "\n".join(f"  > {line}" for line in cf["ai_policy_lines"]))
    if f.get("newcomer_labels_found"):
        reminders.append(f"新手標籤：{', '.join(f['newcomer_labels_found'])}")
    if reminders:
        print("**貢獻規定提醒**")
        for x in reminders:
            print(f"- {x}")
    if r["notes"]:
        print("\n**備註**")
        for n in r["notes"]:
            print(f"- {n}")
    print(f"\n（這個專案用了 {r['api_calls']} 次 GitHub API）\n")


# ---------------------------------------------------------------- opportunities

LOCALE_PARENTS = {"locales", "locale", "i18n", "l10n", "lang", "langs", "languages", "translations",
                  "translation", "messages", "po", "docs", "doc", "content"}
LANG_CODES = {"ar", "bg", "bn", "ca", "cs", "da", "de", "el", "en", "eo", "es", "et", "eu", "fa", "fi", "fr",
              "gl", "he", "hi", "hr", "hu", "hy", "id", "it", "ja", "ka", "kk", "km", "ko", "lt", "lv", "mk",
              "ml", "mn", "ms", "my", "nb", "ne", "nl", "nn", "no", "pl", "pt", "ro", "ru", "si", "sk", "sl",
              "sq", "sr", "sv", "sw", "ta", "te", "th", "tl", "tr", "uk", "ur", "uz", "vi", "zh"}
LOCALE_RE = re.compile(r"^([a-z]{2})([-_]([a-z]{2}|[a-z]{4}|[0-9]{3}))?$", re.I)
SOURCE_EXT = {".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".rs", ".java", ".kt", ".rb", ".php", ".cs",
              ".c", ".cc", ".cpp", ".swift", ".dart", ".scala", ".ex"}
SKIP_DIRS = {"vendor", "node_modules", "third_party", "thirdparty", "external", "dist", "build", "out",
             "examples", "example", "samples", "docs", "doc", "migrations", "benchmarks", "bench",
             "fixtures", ".github", "scripts", "tools"}
TEST_DIRS = {"test", "tests", "__tests__", "spec", "specs", "testing", "test_utils"}
# Case-sensitive on purpose: "FooTest" is a test, "latest" is not.
TEST_NAME_RE = re.compile(r"(^tests?$|^test_|_tests?$|\.test$|\.spec$|_spec$|[a-z0-9]Tests?$)")


def locale_of(part):
    stem = re.sub(r"\.(json|ya?ml|po|pot|properties|ts|js|md|mdx|xliff|xlf|strings|arb|resx|toml|ini)$",
                  "", part, flags=re.I)
    m = LOCALE_RE.match(stem)
    if m and m.group(1).lower() in LANG_CODES:
        return stem.lower().replace("_", "-")
    return None


def scan_tree(gh, repo, branch, cfg):
    tree, _ = gh.get(f"/repos/{repo}/git/trees/{urllib.parse.quote(branch)}", {"recursive": "1"})
    blobs = [t for t in tree.get("tree", []) if t.get("type") == "blob"]
    out = {"truncated": bool(tree.get("truncated")), "total_files": len(blobs)}

    # Translations
    locales = set()
    for b in blobs:
        parts = b["path"].split("/")
        for i in range(1, len(parts)):
            if parts[i - 1].lower() in LOCALE_PARENTS:
                loc = locale_of(parts[i])
                if loc:
                    locales.add(loc)
        if parts[-1].lower().endswith(".po"):
            loc = locale_of(parts[-1])
            if loc:
                locales.add(loc)
    targets = [t.lower().replace("_", "-") for t in cfg.get("target_locales", [])]
    has_target = sorted(l for l in locales if l in targets)
    out["translation"] = {
        "locales_found": sorted(locales),
        "target_locales": targets,
        "target_present": has_target,
        "has_i18n": len(locales) >= 2,
    }

    # Tests
    sources, test_stems, test_count = [], set(), 0
    for b in blobs:
        path = b["path"]
        parts = path.split("/")
        name = parts[-1]
        stem, ext = os.path.splitext(name)
        if ext.lower() not in SOURCE_EXT or name.endswith(".d.ts"):
            continue
        dirs = {p.lower() for p in parts[:-1]}
        is_test = bool(dirs & TEST_DIRS) or bool(TEST_NAME_RE.search(stem))
        if is_test:
            test_count += 1
            base = re.sub(r"(^test_|_tests?$|\.test$|\.spec$|_spec$|Tests?$)", "", stem)
            test_stems.add(base.lower())
            continue
        if dirs & SKIP_DIRS or stem.startswith((".", "__")) or stem in ("setup", "conftest", "main", "index", "mod", "lib") \
                or re.search(r"\.(config|conf)$", stem):
            continue
        sources.append({"path": path, "stem": stem.lower(), "size": b.get("size", 0)})
    untested = [s for s in sources if s["stem"] not in test_stems and len(s["stem"]) > 2]
    # Medium-sized files are the friendliest first test targets.
    picks = sorted((s for s in untested if 800 <= s["size"] <= 15000), key=lambda s: s["size"])
    out["tests"] = {
        "source_files": len(sources),
        "test_files": test_count,
        "untested_count": len(untested),
        "untested_candidates": [{"path": s["path"], "size": s["size"]} for s in picks[:10]],
    }
    return out


def collect_opportunities(gh, repo, cfg, limit):
    info, _ = gh.get(f"/repos/{repo}")
    labels = get_labels(gh, repo)
    groups = {"newcomer": cfg["newcomer_labels"], **cfg["contribution_type_labels"]}
    result = {"repo": repo, "url": info["html_url"], "groups": {}, "notes": []}
    for group, patterns in groups.items():
        matched = match_labels(labels, patterns)
        issues = find_issues_with_labels(gh, repo, matched, limit)[:limit] if matched else []
        result["groups"][group] = {"labels": matched, "issues": issues}
    try:
        result["repo_scan"] = scan_tree(gh, repo, info["default_branch"], cfg)
    except GitHubError as e:
        result["repo_scan"] = None
        result["notes"].append(f"掃描檔案結構失敗：{e}")
    result["api_calls"] = gh.calls
    return result


GROUP_ZH = {"newcomer": "新手 issue", "docs": "文件", "translation": "翻譯", "tests": "測試", "bug": "Bug"}


def print_opportunities(r):
    print(f"# {r['repo']} 可以貢獻的點\n")
    print("條件：open、沒人被指派（no assignee）、還沒有關聯的 PR，由新到舊排序。⚠️ 口頭認領（如「I'll take this」）這裡看不到，推薦前請用 `claims` 指令檢查。\n")
    for group, g in r["groups"].items():
        title = GROUP_ZH.get(group, group)
        if not g["labels"]:
            print(f"## {title}\n專案沒有對應的標籤。\n")
            continue
        print(f"## {title}（標籤：{', '.join(g['labels'])}）")
        if not g["issues"]:
            print("目前沒有符合條件的 issue。\n")
            continue
        print("| # | 標題 | 留言 | 建立 | 最後更新 | 標籤 |\n|---|---|---|---|---|---|")
        for it in g["issues"]:
            stale = " 🕸️" if it["age_days"] > 365 else ""
            print(f"| [{it['number']}]({it['url']}) | {it['title'][:70]} | {it['comments']} | "
                  f"{it['age_days']} 天前{stale} | {it['updated_days_ago']} 天前 | {', '.join(it['labels'][:4])} |")
        print()
    scan = r.get("repo_scan")
    if scan:
        print("## 從檔案結構看到的機會（推測，需人工確認）")
        if scan["truncated"]:
            print("- 專案太大，檔案清單被截斷，以下只看到部分檔案。")
        t = scan["translation"]
        if t["has_i18n"]:
            locs = ", ".join(t["locales_found"][:25])
            if t["target_present"]:
                print(f"- 翻譯：已有 {', '.join(t['target_present'])}，可以檢查是否落後英文版、有沒有缺字串。（偵測到的語系：{locs}）")
            else:
                print(f"- 翻譯：有多語系，但沒有看到 {', '.join(t['target_locales'])}，可能可以新增。（偵測到的語系：{locs}）先確認專案是否用 Crowdin/Weblate/Transifex 等平台管理翻譯。")
        else:
            print("- 翻譯：沒有偵測到多語系結構。")
        ts = scan["tests"]
        print(f"- 測試：{ts['source_files']} 個原始碼檔、{ts['test_files']} 個測試檔，"
              f"約 {ts['untested_count']} 個檔案找不到同名測試。")
        if ts["untested_candidates"]:
            print("  適合當第一個補測試目標的檔案（中等大小、找不到對應測試）：")
            for c in ts["untested_candidates"]:
                print(f"  - `{c['path']}`（{c['size'] / 1024:.1f} KB）")
            print("  注意：這是用檔名比對的推測。Rust 等語言常把測試寫在同一個檔案裡，也有專案用不同命名，請先打開確認。")
    for n in r["notes"]:
        print(f"- {n}")
    print(f"\n（使用了 {r['api_calls']} 次 GitHub API）")


# ---------------------------------------------------------------- claims (stage 3)

# "I'll take this", "can I work on this?", "please assign me", "我來做" ...
CLAIM_RE = re.compile(
    r"\b(i'?m|i am|i will|i'?ll|i would|i'?d|can i|could i|may i|let me|i want to|i'?m going to|i am going to)\b"
    r"[^.?!\n]{0,40}\b(work|take|pick|tackle|handle|fix|implement|attempt|submit|grab)\b"
    r"|\bassign (this |it )?(issue )?(to )?me\b|\bplease assign\b|\bworking on (this|it)\b|\bi'?m on it\b"
    r"|我來|我想(做|試|處理|認領)|可以給我|指派給我",
    re.I)
STALE_CLAIM_DAYS = 30
CLAIM_RANK = {"clear": 0, "maybe": 1, "taken": 2}


def check_claims(gh, repo, number):
    """Is someone already working on this issue? Reads comments and PR cross-references (2-3 API calls)."""
    issue, _ = gh.get(f"/repos/{repo}/issues/{number}")
    result = {"number": number, "title": issue.get("title"), "url": issue.get("html_url"),
              "status": "clear", "reasons": []}

    def flag(status, reason):
        if CLAIM_RANK[status] > CLAIM_RANK[result["status"]]:
            result["status"] = status
        result["reasons"].append(reason)

    if "pull_request" in issue:
        flag("taken", "這是 PR，不是 issue")
        return result
    if issue.get("state") != "open":
        flag("taken", "issue 已經關閉")
    if issue.get("assignees"):
        flag("taken", f"已指派給 {', '.join('@' + a['login'] for a in issue['assignees'])}")

    comments = []
    if issue.get("comments", 0):
        comments, _ = gh.get(f"/repos/{repo}/issues/{number}/comments", {"per_page": 100})
    for c in comments:
        if is_bot(c.get("user")) or not CLAIM_RE.search(c.get("body") or ""):
            continue
        who = c["user"]["login"]
        said = parse_ts(c["created_at"])
        # The claimer's latest activity in this thread, e.g. "still on it, PR soon".
        last = max([said] + [parse_ts(x["created_at"]) for x in comments
                             if (x.get("user") or {}).get("login") == who])
        snippet = re.sub(r"\s+", " ", c.get("body") or "").strip()[:80]
        idle = days_between(last)
        if idle <= STALE_CLAIM_DAYS:
            followup = f"（最近一次留言在 {idle:.0f} 天前）" if last > said else ""
            flag("taken", f"@{who} {days_between(said):.0f} 天前說要做{followup}：「{snippet}」")
        else:
            flag("maybe", f"@{who} {days_between(said):.0f} 天前說要做，之後 {idle:.0f} 天沒有動靜：「{snippet}」")

    timeline, _ = gh.get(f"/repos/{repo}/issues/{number}/timeline", {"per_page": 100})
    for ev in timeline:
        if ev.get("event") != "cross-referenced":
            continue
        src = (ev.get("source") or {}).get("issue") or {}
        if "pull_request" not in src:
            continue
        url = src.get("html_url", "")
        if src.get("state") == "open":
            flag("taken", f"有開著的 PR 提到這個 issue：{url}")
        elif (src.get("pull_request") or {}).get("merged_at"):
            flag("taken", f"已經有 PR 被合併，問題可能已解決：{url}")
        else:
            flag("maybe", f"有人送過 PR 但被關閉，可以看看原因：{url}")
    return result


CLAIM_ZH = {"clear": "🟢 看起來沒人在做", "maybe": "🟡 可能有人做過", "taken": "🔴 有人在做"}


def print_claims(repo, rows):
    print(f"# {repo} 認領檢查\n")
    print("| # | 標題 | 狀態 | 原因 |\n|---|---|---|---|")
    for r in rows:
        if "error" in r:
            print(f"| {r['number']} | ⚠️ {r['error']} | | |")
            continue
        title = (r["title"] or "").replace("|", "\\|")[:60]
        reasons = "<br>".join(x.replace("|", "\\|") for x in r["reasons"]) or "—"
        print(f"| [{r['number']}]({r['url']}) | {title} | {CLAIM_ZH[r['status']]} | {reasons} |")
    print("\n- 🔴 不要推薦。🟡 可以推薦，但要跟學生說明；到階段 4 認領時，先禮貌詢問原本的人是否還在做。")
    print("- 這是用字眼比對，可能誤判（例如「I'd like to take a look」也會被抓到），🔴🟡 請點進去讀那則留言確認。")


# ---------------------------------------------------------------- quick (stage 1)

def collect_quick(gh, repo):
    """Stage 1 check: link, summary, size, and whether there is a contribution guide. 2–3 API calls."""
    info, _ = gh.get(f"/repos/{repo}")
    row = {
        "repo": info["full_name"],
        "url": info["html_url"],
        "description": info.get("description"),
        "language": info.get("language"),
        "stars": info.get("stargazers_count"),
        "topics": info.get("topics", []),
        "archived": info.get("archived", False),
        "contributing": None,
        "contributing_url": None,
    }
    guide = find_contributing(gh, repo)
    if guide is not None:
        row["contributing"] = guide["source"]   # "file", "readme", or None = no guide
        row["contributing_url"] = guide["url"]
    else:
        row["contributing"] = "unknown"
    return row


def print_quick(rows):
    print("| 專案 | 簡介 | 語言 | ⭐ | 貢獻說明 |\n|---|---|---|---|---|")
    for r in rows:
        if "error" in r:
            print(f"| {r['repo']} | ⚠️ {r['error']} | | | |")
            continue
        name = f"[{r['repo']}]({r['url']})" + ("（已封存）" if r["archived"] else "")
        if r["contributing"] == "unknown":
            contrib = "？請手動確認"
        elif r["contributing"] == "file":
            contrib = f"[有，CONTRIBUTING 檔案]({r['contributing_url']})" if r["contributing_url"] else "有，CONTRIBUTING 檔案"
        elif r["contributing"] == "readme":
            contrib = f"[有，README 段落]({r['contributing_url']})" if r["contributing_url"] else "有，README 段落"
        else:
            contrib = "❌ 沒有"
        desc = (r["description"] or "（沒有簡介，請看 README）").replace("|", "\\|")[:100]
        print(f"| {name} | {desc} | {r['language'] or '—'} | {r['stars']} | {contrib} |")
    print("\n沒有貢獻說明（CONTRIBUTING 檔案或 README 段落）或已封存的專案不推薦。簡介是專案原文，推薦給學生時請改寫成白話摘要。")


# ---------------------------------------------------------------- main

def use_utf8_output():
    """Windows consoles and pipes often default to cp950/cp1252, which can't print emoji or all CJK."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass


def main():
    use_utf8_output()
    ap = argparse.ArgumentParser(description="開源專案新手適合度分析")
    sub = ap.add_subparsers(dest="cmd", required=True)
    h = sub.add_parser("health", help="階段 2：評估一個或多個專案")
    h.add_argument("repos", nargs="+", help="一個或多個 OWNER/REPO 或 GitHub 網址")
    h.add_argument("--config", help="自訂設定檔（只需寫要覆蓋的欄位）")
    h.add_argument("--json", action="store_true", help="輸出 JSON")
    o = sub.add_parser("opportunities", help="階段 3：找可以貢獻的點")
    o.add_argument("repo", help="OWNER/REPO 或 GitHub 網址")
    o.add_argument("--config", help="自訂設定檔（只需寫要覆蓋的欄位）")
    o.add_argument("--limit", type=int, default=8, help="每類最多列幾個 issue")
    o.add_argument("--json", action="store_true", help="輸出 JSON")
    c = sub.add_parser("claims", help="階段 3：推薦前檢查 issue 有沒有人在做")
    c.add_argument("repo", help="OWNER/REPO 或 GitHub 網址")
    c.add_argument("issues", nargs="+", type=int, help="issue 編號，可以多個")
    c.add_argument("--json", action="store_true", help="輸出 JSON")
    q = sub.add_parser("quick", help="階段 1：確認連結、簡介、有沒有貢獻說明（可一次多個專案）")
    q.add_argument("repos", nargs="+", help="一個或多個 OWNER/REPO 或 GitHub 網址")
    q.add_argument("--json", action="store_true", help="輸出 JSON")
    args = ap.parse_args()

    if args.cmd == "quick":
        gh = GitHub(find_token())
        rows = []
        for text in args.repos:
            repo = normalize_repo(text)
            try:
                rows.append(collect_quick(gh, repo))
            except GitHubError as e:
                rows.append({"repo": repo, "error": str(e)})
        print(json.dumps(rows, ensure_ascii=False, indent=2)) if args.json else print_quick(rows)
        return

    cfg = load_config(getattr(args, "config", None))  # claims has no --config
    token = find_token()
    if not token:
        print("（沒有偵測到 GitHub token，每小時只有 60 次額度。建議先 `gh auth login` 或設定 GITHUB_TOKEN）",
              file=sys.stderr)
    gh = GitHub(token)

    if args.cmd == "health":
        results = []
        for text in args.repos:
            repo = normalize_repo(text)
            try:
                results.append(collect_health(gh, repo, cfg))
            except GitHubError as e:
                results.append({"repo": repo, "error": str(e)})
        print(json.dumps(results, ensure_ascii=False, indent=2)) if args.json else print_health(results, cfg)
        if all("error" in r for r in results):
            sys.exit(1)
        return

    repo = normalize_repo(args.repo)
    if args.cmd == "claims":
        rows = []
        for n in args.issues:
            try:
                rows.append(check_claims(gh, repo, n))
            except GitHubError as e:
                rows.append({"number": n, "error": str(e)})
        print(json.dumps(rows, ensure_ascii=False, indent=2)) if args.json else print_claims(repo, rows)
        return
    try:
        r = collect_opportunities(gh, repo, cfg, args.limit)
        print(json.dumps(r, ensure_ascii=False, indent=2)) if args.json else print_opportunities(r)
    except GitHubError as e:
        print(f"錯誤：{e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
