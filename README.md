<div align="center">

# oss-first-contribution

**An agent skill that mentors open source beginners from zero to their first merged pull request.**

[![test](https://github.com/Howardisme/oss-first-contribution/actions/workflows/test.yml/badge.svg)](https://github.com/Howardisme/oss-first-contribution/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-blue.svg)
![Works with Claude Code, Codex and Copilot](https://img.shields.io/badge/works%20with-Claude%20Code%20%7C%20Codex%20%7C%20Copilot-8A2BE2.svg)

English | [繁體中文](README.zh-TW.md)

</div>

---
**Open source doesn't ask for your title. It asks for your code.**

Most beginners who want to contribute to open source get stuck before writing a single line: they don't know which project to pick, whether anyone will review their PR, or what a reasonable first task looks like. `oss-first-contribution` is a [skill](https://agentskills.io) for AI coding assistants that walks you through the whole journey, the way a patient senior contributor would.

## Features

- **Starts from real needs to find projects truly worth contributing to.** It asks about your hobbies, daily pain points, and what you want to learn, then finds projects that match. People keep contributing to things they actually use.
- **Checks whether a project really welcomes newcomers.** A bundled script scores repositories on how often outside PRs get merged, how fast humans (not bots) respond, maintainer sustainability (bus factor), and more. It also flags contribution barriers such as "PRs without an approved issue are closed automatically."
- **Finds a first task that fits.** It surfaces open, unassigned issues and missing translations or tests, then checks the comments for "I'll take this" so you don't collide with someone already working on it.
- **Guides the actual work.** Claiming the issue, forking, setting up the environment, reading unfamiliar code, and following the project's template to write a PR maintainers want to merge.
- **Keeps you responsible for your work.** The assistant explains every change so you can defend it in review, and it follows each project's AI policy.
- **Custom metrics.** Metric weights, thresholds, labels, and target languages live in one config file. You can also add your own subjective criteria, such as "will I learn something here?"

## Quick start

> [!IMPORTANT]
> **Before you start, check two things:**
>
> 1. **Install [Python 3.8+](https://www.python.org/downloads/) and the [GitHub CLI](https://github.com/cli/cli#installation), then sign in with `gh auth login`.** Without signing in, GitHub allows only 60 requests per hour, enough to evaluate about one project.
> 2. **Using Codex? Approve network access when it asks.** Codex's sandbox has networking off by default, and the analysis script needs to reach `api.github.com`. To keep it on, see [allow network access](INSTALL.md#codex-allow-network-access).

**Claude Code**

```bash
claude plugin install oss-first-contribution --marketplace Howardisme/oss-first-contribution
```

**Codex**

```bash
codex plugin marketplace add Howardisme/oss-first-contribution
codex plugin add oss-first-contribution@oss-first-contribution
```

**GitHub Copilot** (add the skill folder manually)

```bash
git clone https://github.com/Howardisme/oss-first-contribution.git
cd oss-first-contribution
mkdir -p ~/.copilot/skills
cp -r skills/oss-first-contribution ~/.copilot/skills/
```

Then start a new session and say:

> I'm new to open source and want to make my first contribution.

The skill triggers automatically when you talk about contributing to open source. In Copilot, switch to **Agent** mode first; it asks before running `analyze_repo.py`, so approve it.

For Windows commands, updating, manual installs for Claude Code or Codex, and Codex token setup, see [INSTALL.md](INSTALL.md).

## How it works

The skill guides you through seven stages. Each stage ends with you making a choice before moving on.

| Stage | What happens |
|---|---|
| **0 · Get to know you** | Explains why to start from things you use every day, then explores interests → pain points → what you want to learn |
| **1 · Find candidates** | Recommends 5 projects with a link, a plain-language summary, and why each fits. Only projects with a contribution guide (a `CONTRIBUTING` file or a README section) make the list |
| **2 · Evaluate** | You pick what matters to you, then the script scores the projects in three layers: basic facts (not scored), objective metrics (scored), and subjective criteria the assistant judges with evidence |
| **3 · Pick an issue** | Surfaces open, unassigned issues (newest first), checks for informal claims, and recommends 2–3 with the reasoning behind each |
| **4 · Do the work** | Claim the issue, fork, set up the environment, understand the code, make the change, run the tests |
| **5 · Open the PR** | Open it on GitHub, fill in the project's PR template, read CI and bot comments, respond to review |
| **6 · Wrap up** | Clean up the fork, reflect, and share your experience here |

### Evaluation metrics

| Group | Metrics | Default weight |
|---|---|---|
| Activity | Days since last commit (tiered: ≤14 days is "very active"), recent commits, recent merged PRs | 15 |
| Friendliness to outside contributors | Outside PR merge rate, outside PR time to merge, time to first human maintainer response | 50 |
| Maintainer responsiveness | Issue response rate, time to first response, issue close ratio | 20 |
| Newcomer entry points | Open, unassigned issues with newcomer labels | 5 |
| Sustainability | Bus factor, number of core team members | 10 |

A few design choices keep the score honest:

- **Bots and auto-closes don't count as responses.** Only human replies from the core team count. Many projects auto-close PRs that skip their process, which would otherwise look like an instant response.
- **Employees aren't counted as outside contributors.** Frequent committers are treated as core team even when their org membership is private.
- **Floors.** If the outside PR merge rate is below 30% or the issue response rate is below 50%, the verdict is capped at "proceed with caution", however high the total.

Full definitions are in [`references/metrics.md`](skills/oss-first-contribution/references/metrics.md), and all thresholds can be changed in [`config.json`](skills/oss-first-contribution/config.json).

> **Language:** the skill's instructions are written in Traditional Chinese, but the assistant replies in whatever language you use.

## Contributing

All kinds of contributions are welcome:

- **Share your experience.** After your first contribution, add your story to [`experiences/`](experiences/): which project you picked, where you got stuck, and how you got unstuck.
- **Report problems or suggest features** with the issue templates.
- **Pick up an issue** labeled [`good first issue`](https://github.com/Howardisme/oss-first-contribution/labels/good%20first%20issue).

See [CONTRIBUTING.md](CONTRIBUTING.md) for the project structure, how to run the tests, and more.

## Acknowledgements

The evaluation metrics draw on the work of the [CHAOSS](https://chaoss.community) project on open source community health.

## License

[MIT](LICENSE)
