"""Tests for skills/oss-first-contribution/scripts/analyze_repo.py.

No network: every GitHub API call goes to FakeGitHub below.
Run from the repo root:  python -m unittest discover -s tests -v
"""

import base64
import contextlib
import importlib.util
import io
import json
import re
import sys
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from unittest import mock

SCRIPT = Path(__file__).resolve().parent.parent / "skills" / "oss-first-contribution" / "scripts" / "analyze_repo.py"
spec = importlib.util.spec_from_file_location("analyze_repo", SCRIPT)
ar = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ar)


def ago(days):
    return ar.iso(ar.NOW - timedelta(days=days))


def user(login, kind="User"):
    return {"login": login, "type": kind}


def b64(text):
    return base64.b64encode(text.encode()).decode()


# ---------------------------------------------------------------- fake GitHub

CONTRIBUTING = "# Contributing\nPlease sign the CLA before your first PR.\nAI-generated code must be disclosed.\nWe maintain this.\n"
README_WITH_SECTION = "# Readme-only\nA tool.\n## How to contribute\nOpen an issue first. Sign-off your commits (DCO).\n## License\nMIT\n"
README_WITHOUT = "# No guide\nJust a tool.\n## Contributors\nalice, bob\n"


def repo_info(name, **extra):
    info = {"full_name": name, "html_url": f"https://github.com/{name}", "description": f"{name} description",
            "stargazers_count": 12345, "forks_count": 300, "language": "Python", "license": {"spdx_id": "MIT"},
            "created_at": "2019-05-01T00:00:00Z", "topics": ["music"], "archived": False, "has_issues": True,
            "open_issues_count": 50, "default_branch": "main", "owner": {"login": "alice", "type": "User"}}
    info.update(extra)
    return info


def search_item(number, title, labels, created, updated, comments=0):
    return {"number": number, "title": title, "html_url": f"https://github.com/music/tabkit/issues/{number}",
            "labels": [{"name": l} for l in labels], "comments": comments,
            "created_at": ago(created), "updated_at": ago(updated)}


NEWCOMER_ITEMS = [
    search_item(5, "Old docs cleanup", ["good first issue", "documentation"], 400, 100),
    search_item(11, "Add tests for parse_tab", ["good first issue", "tests"], 10, 2, 1),
    search_item(12, "Fix capo display", ["good first issue"], 3, 1, 1),
    search_item(13, "Support drop D tuning", ["good first issue"], 70, 60, 1),
]

TREE = [("src/tabkit/parser.py", 4000), ("src/tabkit/latest.py", 3000), ("src/tabkit/core.py", 9000),
        ("src/tabkit/__init__.py", 100), ("tests/test_core.py", 2000), ("docs/index.md", 500),
        ("locales/en.json", 300), ("locales/ja.json", 300), ("locales/zh_CN.json", 300),
        ("web/src/Fretboard.tsx", 5000), ("web/src/Fretboard.test.tsx", 900), ("web/src/Card.tsx", 1200),
        ("node_modules/a/b.js", 5000)]


def tabkit_commits(params):
    if "page" in params:  # sustainability listing
        authors = ["alice"] * 40 + ["bob"] * 15 + ["carol"] * 10 + ["dave"] * 5
        out = [{"author": user(a), "commit": {"author": {"name": a}}} for a in authors]
        out += [{"author": user("dependabot[bot]", "Bot")}] * 10
        out += [{"author": None, "commit": {"author": {"name": "anon-dev"}}}] * 5
        return out, {}
    if "since" in params:  # counted via the Link header
        return [{}], {"link": '<https://api.github.com/x?page=12>; rel="last"'}
    return [{"commit": {"committer": {"date": ago(20)}}}], {}


def tabkit_search(q):
    q = q.lower()
    if "is:pr is:open" in q:
        return {"total_count": 8}
    if "is:pr is:merged" in q:
        return {"total_count": 6}
    if "is:issue created:>=" in q:
        return {"total_count": 20}
    if "is:issue is:closed closed:>=" in q:
        return {"total_count": 15}
    m = re.search(r'label:"([^"]+)"', q)
    if m:
        items = [i for i in NEWCOMER_ITEMS if m.group(1) in [l["name"] for l in i["labels"]]]
        return {"total_count": len(items), "items": items}
    return {"total_count": 0, "items": []}


def tabkit_pulls(params):
    if params["state"] == "closed":
        prs = [{"number": 100 + i, "user": user(f"ext{i}"), "author_association": "CONTRIBUTOR" if i % 2 else "NONE",
                "created_at": ago(40 + i), "closed_at": ago(35 + i), "merged_at": ago(35 + i) if i < 5 else None}
               for i in range(10)]
        prs.append({"number": 200, "user": user("bob"), "author_association": "MEMBER",
                    "created_at": ago(12), "closed_at": ago(11), "merged_at": ago(11)})
        prs.append({"number": 201, "user": user("renovate[bot]", "Bot"), "author_association": "NONE",
                    "created_at": ago(3), "closed_at": ago(2), "merged_at": ago(2)})
        return prs
    prs = [{"number": 300 + i, "user": user(f"new{i}"), "author_association": "FIRST_TIME_CONTRIBUTOR",
            "created_at": ago(10 + i), "closed_at": None} for i in range(5)]
    prs.append({"number": 399, "user": user("carol"), "author_association": "COLLABORATOR",
                "created_at": ago(4), "closed_at": None})
    return prs


CLAIM_THREADS = {
    11: ([{"user": user("carol"), "author_association": "COLLABORATOR", "body": "Tests should go in tests/test_parser.py", "created_at": ago(6)}], []),
    12: ([{"user": user("amy"), "author_association": "NONE", "body": "Hi, can I work on this?", "created_at": ago(1)}], []),
    13: ([{"user": user("ben"), "author_association": "NONE", "body": "I'll take this one!", "created_at": ago(60)}], []),
    14: ([], [{"event": "cross-referenced", "source": {"issue": {"html_url": "https://github.com/music/tabkit/pull/9",
                                                                 "state": "open", "pull_request": {"merged_at": None}}}}]),
}


GATED_GUIDE = (
    "# Contributing\n"
    "If you haven't had a PR merged here yet, start from an issue a maintainer has labeled `accepted`.\n"
    "PRs from new contributors that aren't linked to an accepted issue are closed automatically.\n"
    "CI checks are mostly for internal use.\n"
)


def gated_routes(rest, params):
    """corp/gated: employees without public org membership, bot auto-closes, nobody answers issues."""
    if rest == "":
        return repo_info("corp/gated", owner={"login": "corp", "type": "Organization"}), {}
    if rest == "/commits":
        if "page" in params:
            authors = ["emp1"] * 30 + ["emp2"] * 10 + ["ext0"]
            return [{"author": user(a), "commit": {"author": {"name": a}}} for a in authors], {}
        if "since" in params:
            return [{}], {"link": '<https://api.github.com/x?page=30>; rel="last"'}
        return [{"commit": {"committer": {"date": ago(1)}}}], {}
    if rest == "/contributors":
        return [{}], {"link": '<https://api.github.com/x?page=40>; rel="last"'}
    if rest == "/pulls" and params["state"] == "closed":
        # Employees show up as CONTRIBUTOR and merge their own PRs within hours.
        prs = [{"number": 600 + i, "user": user("emp1"), "author_association": "CONTRIBUTOR",
                "created_at": ago(20 + i), "closed_at": ago(19.9 + i), "merged_at": ago(19.9 + i)} for i in range(6)]
        # Three outside PRs merged after 10 days, nine closed by a bot within an hour.
        prs += [{"number": 700 + i, "user": user(f"ext{i}"), "author_association": "NONE",
                 "created_at": ago(40 + i), "closed_at": ago(30 + i), "merged_at": ago(30 + i)} for i in range(3)]
        prs += [{"number": 710 + i, "user": user(f"new{i}"), "author_association": "FIRST_TIME_CONTRIBUTOR",
                 "created_at": ago(10 + i), "closed_at": ago(9.96 + i), "merged_at": None} for i in range(9)]
        return prs, {}
    if rest == "/pulls":
        prs = [{"number": 710 + i, "user": user(f"new{i}"), "author_association": "FIRST_TIME_CONTRIBUTOR",
                "created_at": ago(10 + i), "closed_at": ago(9.96 + i), "merged_at": None} for i in range(4)]
        prs.append({"number": 601, "user": user("emp1"), "author_association": "CONTRIBUTOR",
                    "created_at": ago(3), "closed_at": None, "merged_at": None})
        return prs, {}
    if re.match(r"^/pulls/\d+/reviews$", rest):
        return [{"user": {"login": "copilot-pull-request-reviewer", "type": "User"},
                 "author_association": "NONE", "submitted_at": ago(9.99)}], {}
    if re.match(r"^/issues/\d+/comments$", rest):
        n = int(rest.split("/")[2])
        if n >= 700:  # bot comments on the auto-closed PRs
            return [{"user": user("github-actions[bot]", "Bot"), "author_association": "NONE",
                     "body": "Closed: link an accepted issue.", "created_at": ago(9.97)},
                    {"user": {"login": "codecov-commenter", "type": "User"}, "author_association": "NONE",
                     "body": "Coverage report", "created_at": ago(9.98)}], {}
        return [{"user": user("random-user"), "author_association": "NONE", "body": "+1", "created_at": ago(2)}], {}
    if rest == "/issues":
        issues = [{"number": 800 + i, "user": user(f"rep{i}"), "author_association": "NONE",
                   "created_at": ago(8 + i), "comments": 1, "state": "open"} for i in range(5)]
        issues.append({"number": 899, "user": user("emp1"), "author_association": "CONTRIBUTOR",
                       "created_at": ago(5), "comments": 0, "state": "open"})
        return issues, {}
    if rest.startswith("/labels"):
        return [], {}
    if rest == "/community/profile":
        return {"files": {"contributing": {"url": f"{ar.API}/repos/corp/gated/contents/CONTRIBUTING.md",
                                           "html_url": "https://github.com/corp/gated/blob/main/CONTRIBUTING.md"}}}, {}
    if rest == "/contents/CONTRIBUTING.md":
        return {"content": b64(GATED_GUIDE)}, {}
    raise AssertionError(f"unexpected corp/gated{rest} {params}")


class FakeGitHub:
    """Stand-in for GitHub.get: routes API paths to canned responses."""

    def __call__(self, gh, path, params=None):
        gh.calls += 1
        params = params or {}
        p = path.replace(ar.API, "")

        if p.startswith("/search/issues"):
            return tabkit_search(params["q"]), {}

        m = re.match(r"^/repos/([^/]+/[^/]+)(.*)$", p)
        if not m:
            raise AssertionError(f"unexpected path {p}")
        repo, rest = m.groups()

        if repo == "corp/gated":
            return gated_routes(rest, params)
        if repo == "x/missing":
            raise ar.GitHubError(f"找不到 {path}（專案名稱打錯，或是私有專案？）")
        if repo == "old/archived":
            if rest == "":
                return repo_info(repo, archived=True), {}
            if rest == "/community/profile":
                return {"files": {"contributing": {"html_url": "https://github.com/old/archived/blob/main/CONTRIBUTING.md"}}}, {}
        if repo in ("docs/readme-only", "solo/noguide"):
            if rest == "":
                return repo_info(repo, description=None), {}
            if rest == "/community/profile":
                return {"files": {"contributing": None}}, {}
            if rest == "/readme":
                text = README_WITH_SECTION if repo == "docs/readme-only" else README_WITHOUT
                return {"content": b64(text), "html_url": f"https://github.com/{repo}#readme"}, {}
        if repo != "music/tabkit":
            raise AssertionError(f"unexpected {repo}{rest} {params}")

        if rest == "":
            return repo_info(repo), {}
        if rest == "/contributors":
            return [{}], {"link": '<https://api.github.com/x?page=88>; rel="last"'}
        if rest == "/commits":
            return tabkit_commits(params)
        if rest == "/pulls":
            return tabkit_pulls(params), {}
        if re.match(r"^/pulls/\d+/reviews$", rest):
            n = int(rest.split("/")[2])
            if n == 304:
                return [], {}  # never answered
            return [{"user": user("bob"), "submitted_at": ago(10 + (n - 300) - 3)}], {}
        if re.match(r"^/issues/\d+/comments$", rest):
            n = int(rest.split("/")[2])
            if n in CLAIM_THREADS:
                return CLAIM_THREADS[n][0], {}
            if n >= 300:
                return [{"user": user(f"new{n - 300}"), "author_association": "NONE", "created_at": ago(9)}], {}
            return [{"user": user("carol"), "author_association": "COLLABORATOR", "created_at": ago(6)}], {}
        if re.match(r"^/issues/\d+/timeline$", rest):
            n = int(rest.split("/")[2])
            return CLAIM_THREADS.get(n, ([], []))[1], {}
        if re.match(r"^/issues/\d+$", rest):
            n = int(rest.split("/")[2])
            comments = CLAIM_THREADS.get(n, ([], []))[0]
            return {"number": n, "title": f"Issue {n}", "html_url": f"https://github.com/{repo}/issues/{n}",
                    "state": "open", "comments": len(comments), "assignees": []}, {}
        if rest == "/issues":
            return [{"number": 500 + i, "user": user(f"rep{i}"), "created_at": ago(8 + i),
                     "comments": 1 if i % 2 else 0, "state": "open"} for i in range(12)], {}
        if rest.startswith("/labels"):
            return [{"name": n} for n in ["Good First Issue", "documentation", "tests", "bug", "latest-release"]], {}
        if rest == "/community/profile":
            return {"files": {"contributing": {"url": f"{ar.API}/repos/{repo}/contents/CONTRIBUTING.md",
                                               "html_url": f"https://github.com/{repo}/blob/main/CONTRIBUTING.md"}}}, {}
        if rest == "/contents/CONTRIBUTING.md":
            return {"content": b64(CONTRIBUTING)}, {}
        if rest.startswith("/git/trees/"):
            return {"truncated": False, "tree": [{"type": "blob", "path": a, "size": s} for a, s in TREE]}, {}
        raise AssertionError(f"unexpected {repo}{rest} {params}")


class FakeGitHubTestCase(unittest.TestCase):
    def setUp(self):
        fake = FakeGitHub()
        patches = [
            mock.patch.object(ar.GitHub, "get", lambda gh, path, params=None: fake(gh, path, params)),
            mock.patch.object(ar, "find_token", lambda: "test-token"),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        self.gh = ar.GitHub("test-token")
        self.cfg = ar.load_config(None)


def run_cli(*argv):
    """Run analyze_repo.main() with argv; return (stdout, exit_code)."""
    out = io.StringIO()
    code = 0
    with mock.patch.object(sys, "argv", ["analyze_repo.py", *argv]), contextlib.redirect_stdout(out), \
            contextlib.redirect_stderr(io.StringIO()):
        try:
            ar.main()
        except SystemExit as e:
            code = e.code or 0
    return out.getvalue(), code


# ---------------------------------------------------------------- pure helpers

class TestHelpers(unittest.TestCase):
    def test_normalize_repo(self):
        for text in ["https://github.com/a/b.git", "github.com/a/b/", "a/b", "https://github.com/a/b/issues/3"]:
            self.assertEqual(ar.normalize_repo(text), "a/b")

    def test_score_metric_is_linear_and_clamped(self):
        spec = {"good": 10, "bad": 0}
        self.assertEqual(ar.score_metric(5, spec), 50)
        self.assertEqual(ar.score_metric(20, spec), 100)
        self.assertEqual(ar.score_metric(-3, spec), 0)
        self.assertEqual(ar.score_metric(3, {"good": 3, "bad": 45}), 100)  # lower is better
        self.assertIsNone(ar.score_metric(None, spec))

    def test_activity_tiers(self):
        tiers = ar.load_config(None)["activity_tiers"]
        self.assertEqual(ar.activity_tier(3, tiers)["label"], "極度活躍")
        self.assertEqual(ar.activity_tier(14, tiers)["label"], "極度活躍")
        self.assertEqual(ar.activity_tier(20, tiers)["label"], "蠻活躍")
        self.assertEqual(ar.activity_tier(400, tiers)["label"], "不活躍")

    def test_student_config_overrides_only_what_it_sets(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump({"metrics": {"bus_factor": {"weight": 0}}, "basic": ["stars"]}, f)
        cfg = ar.load_config(f.name)
        self.assertEqual(cfg["metrics"]["bus_factor"], {"weight": 0, "good": 3, "bad": 1})
        self.assertEqual(cfg["metrics"]["commits_in_window"]["weight"],
                         ar.load_config(None)["metrics"]["commits_in_window"]["weight"])
        self.assertEqual(cfg["basic"], ["stars"])  # lists replace the default

    def test_label_matching_ignores_case_and_symbols(self):
        labels = ["Good First Issue 🐣", "good-first-issue", "latest-release", "area: tests"]
        self.assertEqual(ar.match_labels(labels, ["good first issue"]), labels[:2])
        self.assertEqual(ar.match_labels(labels, ["tests"]), ["area: tests"])

    def test_locale_detection(self):
        self.assertEqual(ar.locale_of("zh_TW.json"), "zh-tw")
        self.assertEqual(ar.locale_of("ja"), "ja")
        self.assertIsNone(ar.locale_of("index.json"))


class TestContributingSection(unittest.TestCase):
    def test_markdown_section_stops_at_same_level(self):
        md = "# Tool\n## Install\npip\n## Contributing\nPRs welcome!\n### Dev setup\nrun x\n## License\nMIT\n"
        section = ar.contributing_section(md)
        self.assertTrue(section.startswith("## Contributing"))
        self.assertIn("Dev setup", section)
        self.assertNotIn("License", section)

    def test_other_heading_styles(self):
        self.assertTrue(ar.contributing_section("How to contribute\n-----------------\nOpen an issue.\n").startswith("How to"))
        self.assertTrue(ar.contributing_section('<h2 align="center">Contributing</h2>\nYes\n').startswith("<h2"))
        self.assertTrue(ar.contributing_section("# 工具\n## 如何貢獻\n歡迎 PR\n").startswith("## 如何貢獻"))

    def test_contributors_list_is_not_a_guide(self):
        self.assertIsNone(ar.contributing_section("# T\n## Contributors ✨\nalice bob\n"))
        self.assertIsNone(ar.contributing_section("# T\nNo guide here\n"))

    def test_scan_rules(self):
        flags = ar.scan_rules("Please sign the CLA.\nUse git commit -s (DCO).\nNo AI-generated code.\nWe maintain this.")
        self.assertTrue(flags["cla"])
        self.assertTrue(flags["dco"])
        self.assertEqual(flags["ai_policy_lines"], ["No AI-generated code."])  # "maintain" is not "AI"


class TestClaimRegex(unittest.TestCase):
    def test_claims(self):
        for text in ["Hi, can I work on this?", "I'll take this one!", "I'm going to fix this", "please assign me",
                     "Working on it", "我來試試看", "我想認領這個"]:
            self.assertRegex(text, ar.CLAIM_RE, text)

    def test_not_claims(self):
        for text in ["I would love this feature.", "When I tried it, it crashed.", "Thanks for the report",
                     "Does anyone know a workaround?"]:
            self.assertNotRegex(text, ar.CLAIM_RE, text)


# ---------------------------------------------------------------- commands with fake GitHub

class TestQuick(FakeGitHubTestCase):
    def test_guide_sources(self):
        rows = {r["repo"]: r for r in (ar.collect_quick(self.gh, n) for n in
                                       ["music/tabkit", "docs/readme-only", "solo/noguide", "old/archived"])}
        self.assertEqual(rows["music/tabkit"]["contributing"], "file")
        self.assertEqual(rows["docs/readme-only"]["contributing"], "readme")
        self.assertIsNone(rows["solo/noguide"]["contributing"])
        self.assertTrue(rows["old/archived"]["archived"])


class TestHealth(FakeGitHubTestCase):
    def test_metrics(self):
        r = ar.collect_health(self.gh, "music/tabkit", self.cfg)
        m = {row["metric"]: row for row in r["metrics"]}
        self.assertEqual(r["basic"]["open_issues"], 42)          # 50 open minus 8 open PRs
        self.assertEqual(r["basic"]["contributors"], 88)
        self.assertEqual(r["activity_label"], "蠻活躍")           # last commit 20 days ago
        self.assertEqual(m["outside_pr_merge_rate"]["value"], 0.5)
        self.assertEqual(m["bus_factor"]["value"], 1)            # alice: 40 of 75 human commits
        self.assertEqual(m["active_maintainers"]["value"], 4)    # alice, bob, carol, dave commit often
        self.assertEqual(r["facts"]["pr_response_unanswered"], 1)
        self.assertEqual(r["facts"]["contributing_source"], "file")
        self.assertTrue(r["facts"]["contributing_flags"]["cla"])
        th = self.cfg["verdict_thresholds"]
        expected = ("recommended" if r["overall_score"] >= th["recommended"]
                    else "caution" if r["overall_score"] >= th["caution"] else "not_recommended")
        self.assertEqual(r["verdict"], expected)

    def test_weight_zero_hides_metric(self):
        cfg = ar.deep_merge(self.cfg, {"metrics": {"bus_factor": {"weight": 0}}})
        r = ar.collect_health(self.gh, "music/tabkit", cfg)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            ar.print_health([r], cfg)
        self.assertNotIn("Bus factor", out.getvalue())


class TestGatedCompanyRepo(FakeGitHubTestCase):
    """Regression: inspect_ai / deepeval looked beginner-friendly because of bots, auto-closes and employees."""

    def setUp(self):
        super().setUp()
        self.r = ar.collect_health(self.gh, "corp/gated", self.cfg)
        self.m = {row["metric"]: row["value"] for row in self.r["metrics"]}

    def test_frequent_committers_are_core_even_without_member_badge(self):
        self.assertIn("emp1", self.r["facts"]["core_team"])
        self.assertEqual(self.r["facts"]["outside_prs_sampled"], 12)   # emp1's 6 PRs are not "outside"

    def test_merge_speed_uses_outside_prs_only(self):
        self.assertAlmostEqual(self.m["median_days_to_merge"], 10, places=0)  # not emp1's 0.1 days
        self.assertEqual(self.m["outside_pr_merge_rate"], 0.25)

    def test_bot_comments_and_auto_close_are_not_responses(self):
        self.assertEqual(self.r["facts"]["pr_response_unanswered"], self.r["facts"]["pr_response_sampled"])
        self.assertGreater(self.m["outside_pr_first_response_days"], 5)   # not 0.1 days

    def test_only_core_replies_count_on_issues(self):
        self.assertEqual(self.m["issue_response_rate"], 0)  # "+1" from a random user is not an answer
        self.assertEqual(self.r["facts"]["issues_sampled"], 5)  # emp1's own issue is excluded

    def test_caps_stop_a_misleading_recommendation(self):
        self.assertNotEqual(self.r["verdict"], "recommended")
        self.assertEqual(len(self.r["caps"]), 2)

    def test_contribution_barriers_are_flagged(self):
        gates = self.r["facts"]["contributing_flags"]["gate_lines"]
        self.assertEqual(len(gates), 3)


class TestBotDetection(unittest.TestCase):
    def test_bots(self):
        for login, kind in [("dependabot[bot]", "Bot"), ("codecov-commenter", "User"), ("github-actions", "User"),
                            ("copilot-pull-request-reviewer", "User"), ("my-release-bot", "User"), ("pre-commit-ci", "User")]:
            self.assertTrue(ar.is_bot({"login": login, "type": kind}), login)

    def test_humans(self):
        for login in ["talbot", "robotics-fan", "abbott", "alice"]:
            self.assertFalse(ar.is_bot({"login": login, "type": "User"}), login)


class TestClaims(FakeGitHubTestCase):
    def test_statuses(self):
        got = {n: ar.check_claims(self.gh, "music/tabkit", n)["status"] for n in (11, 12, 13, 14)}
        self.assertEqual(got, {11: "clear", 12: "taken", 13: "maybe", 14: "taken"})


# ---------------------------------------------------------------- end to end: the stages in order

class TestPluginManifests(unittest.TestCase):
    """The plugin files must agree with each other and with the skill, or installs break."""

    ROOT = SCRIPT.parent.parent.parent.parent

    def load(self, rel):
        return json.loads((self.ROOT / rel).read_text(encoding="utf-8"))

    def test_names_and_versions_agree(self):
        claude = self.load(".claude-plugin/plugin.json")
        codex = self.load(".codex-plugin/plugin.json")
        self.assertEqual(claude["name"], codex["name"])
        self.assertEqual(claude["version"], codex["version"], "bump both plugin.json versions together")
        market = self.load(".claude-plugin/marketplace.json")
        self.assertEqual(market["plugins"][0]["name"], claude["name"])
        self.assertEqual(self.load(".agents/plugins/marketplace.json")["plugins"][0]["name"], codex["name"])

    def test_skill_name_matches_folder(self):
        # Copilot silently skips a skill whose name differs from its folder.
        skill = SCRIPT.parent.parent
        front = skill.joinpath("SKILL.md").read_text(encoding="utf-8").split("---")[1]
        name = re.search(r"^name:\s*(\S+)", front, re.M).group(1)
        desc = re.search(r"^description:\s*(.+)$", front, re.M).group(1)
        self.assertEqual(name, skill.name)
        self.assertRegex(name, r"^[a-z0-9-]{1,64}$")
        self.assertLessEqual(len(desc), 1024)


class TestEndToEnd(FakeGitHubTestCase):
    """Stage 1 quick → stage 2 health → stage 3 opportunities → stage 3 claims, through the CLI."""

    def test_full_flow(self):
        # Stage 1: five candidates, one typo
        out, code = run_cli("quick", "music/tabkit", "docs/readme-only", "solo/noguide", "old/archived", "x/missing")
        self.assertEqual(code, 0)
        self.assertIn("有，CONTRIBUTING 檔案", out)
        self.assertIn("有，README 段落", out)
        self.assertIn("❌ 沒有", out)
        self.assertIn("（已封存）", out)
        self.assertIn("⚠️ 找不到", out)

        # Stage 2: the student's own config, plus a typo that must not stop the run
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump({"basic": ["stars", "contributors", "language"],
                       "metrics": {"merged_prs_in_window": {"weight": 0}},
                       "subjective": [{"name": "學得到東西", "how": "有沒有用到 PyTorch", "importance": "高"}]},
                      f, ensure_ascii=False)
        out, code = run_cli("health", "music/tabkit", "x/missing", "--config", f.name)
        self.assertEqual(code, 0)
        for expected in ["## 基礎資訊（不計分）", "| 專案 | ⭐ Star | 貢獻者 | 語言 |", "### 客觀指標", "助手評語",
                         "### 主觀指標", "學得到東西", "助手綜合評分", "需要簽 CLA", "⚠️ 找不到"]:
            self.assertIn(expected, out)
        self.assertNotIn("近期合併的 PR 數", out)  # weight 0 → hidden

        out, code = run_cli("health", "music/tabkit", "--json")
        data = json.loads(out)
        self.assertEqual(data[0]["repo"], "music/tabkit")
        self.assertIn("overall_score", data[0])

        # Stage 3: candidates, newest first, then the claim check
        out, code = run_cli("opportunities", "music/tabkit")
        self.assertEqual(code, 0)
        self.assertIn("新手 issue", out)
        self.assertIn("`claims`", out)
        self.assertLess(out.index("[12]"), out.index("[5]"))  # newest first
        self.assertIn("🕸️", out)                              # the 400-day-old issue
        self.assertIn("zh-tw", out)                            # missing translation
        self.assertIn("src/tabkit/parser.py", out)             # untested file
        self.assertNotIn("src/tabkit/latest.py`（", out.split("找不到對應測試")[0])

        out, code = run_cli("claims", "music/tabkit", "11", "12", "13")
        self.assertEqual(code, 0)
        self.assertRegex(out, r"\[11\].*🟢")
        self.assertRegex(out, r"\[12\].*🔴")
        self.assertRegex(out, r"\[13\].*🟡")

    def test_all_repos_missing_exits_nonzero(self):
        _, code = run_cli("health", "x/missing")
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
