English | [繁體中文](CONTRIBUTING.zh-TW.md)

# Contributing

All kinds of contributions are welcome. Sharing your experience, sharing what you know, reporting a problem, and improving the docs or code all count as open source contributions.

## Ways to contribute

| Type | How |
|---|---|
| Share your experience | Add a story to [`experiences/`](experiences/) and open a PR (see below) |
| Report a problem | Use the *bug report* issue template, and include the conversation excerpt or script output |
| Suggest a feature | Use the *feature request* issue template, and discuss before building |
| Improve the skill, docs, or scripts | Open a PR directly. For larger changes, open an issue to discuss first |

### Sharing your experience

After you finish (or get stuck on) an open source contribution, write it down for the students who come after you. It doesn't matter whether your PR was merged: the parts where you got stuck are often the most useful.

Copy [`experiences/_template.md`](experiences/_template.md) (or the Chinese [`_template.zh-TW.md`](experiences/_template.zh-TW.md)) to `experiences/<your-github-account>-sharing01.md` (use `02`, `03` for later stories), fill it in, and open a PR. You don't need to know git for this: open the `experiences/` folder on GitHub, choose **Add file → Create new file**, and GitHub will walk you through opening the PR.

## Pull requests

- Write issues, PR descriptions, and replies to review in English, just as you would on a large international project
- Fill in the PR template. Write N/A for sections that don't apply
- **If you add or change code in `scripts/`, add unit tests and run the test suite:**

  ```bash
  python -m unittest discover -s tests
  ```

  Tests must not touch the network. Add any fake data you need to `FakeGitHub` in `tests/test_analyze_repo.py`.

## Project structure

```
.
├── skills/oss-first-contribution/   # the skill itself: this folder is what you install
│   ├── SKILL.md                     # main instructions for the assistant (the seven stages)
│   ├── config.json                  # default metrics, weights, thresholds, labels
│   ├── references/                  # detail loaded only when a stage needs it
│   └── scripts/analyze_repo.py      # GitHub API analysis (quick / health / opportunities / claims)
├── .claude-plugin/                  # Claude Code plugin + marketplace manifests
├── .codex-plugin/                   # Codex plugin manifest
├── .agents/plugins/                 # Codex marketplace manifest
├── experiences/                     # students' contribution stories
├── tests/                           # offline tests with a fake GitHub API
└── .github/                         # PR and issue templates, CI
```

## Development

Fork the repository on GitHub, clone your fork, and run the tests once to check your setup:

```bash
git clone https://github.com/<your-username>/oss-first-contribution.git
cd oss-first-contribution
python -m unittest discover -s tests -v
```

The tests never touch the network: every API call goes to a `FakeGitHub` stub in [`tests/test_analyze_repo.py`](tests/test_analyze_repo.py). CI runs them on Python 3.8 and 3.12.

## Changing the skill

- The same rule may appear in several files (`SKILL.md`, `references/`, `config.json`). Update all of them together
- The skill is shared by Claude, Codex, and GitHub Copilot. Don't refer to tools that only one assistant has, and don't change the skill's `name` or its folder name

## About AI

You're welcome to use AI tools, but the PR goes out under your name: review every line you submit and be ready to explain it.

## Respect each other

This is the most important thing in any open source community. Everyone starts as a beginner. 


## A note on language

The skill itself (`SKILL.md` and the files in `references/`) is written in Traditional Chinese, because it was built for a university course in Taiwan. Contributions in English are welcome. The assistant reads either language without trouble, and it always replies to students in the language they use.
