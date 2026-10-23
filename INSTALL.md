English | [繁體中文](INSTALL.zh-TW.md)

# Installation

The fastest way to install is the [Quick start in the README](README.md#quick-start). This page has the full details: requirements, installing and updating for each assistant, Codex network settings, and manual installation.

## Requirements

| Requirement | Why | Install |
|---|---|---|
| Python 3.8+ | Runs the analysis script. Standard library only, no `pip install` needed | [python.org](https://www.python.org/downloads/) |
| GitHub CLI (`gh`) | Authenticates GitHub API calls. Without it you get 60 requests per hour, enough to evaluate about one project | macOS: `brew install gh` · Windows: `winget install --id GitHub.cli` · [others](https://github.com/cli/cli#installation) |
| Claude Code, Codex, or GitHub Copilot | Runs the skill | [Claude Code](https://code.claude.com/docs) · [Codex](https://developers.openai.com/codex) · [Copilot](https://docs.github.com/copilot) |

After installing `gh`, open a **new** terminal (so it is on your `PATH`) and sign in:

```bash
gh auth login     # choose GitHub.com → HTTPS → Login with a web browser
gh auth status    # should print "Logged in to github.com account <you>"
```

## Claude Code plugin

Run in your terminal (Claude Code 2.1.275 or later):

```bash
claude plugin install oss-first-contribution --marketplace Howardisme/oss-first-contribution
```

Start a new session. The skill triggers automatically when you talk about contributing to open source, or invoke it directly with `/oss-first-contribution:oss-first-contribution` (plugin skills are prefixed with the plugin name).

**Update:**

```bash
claude plugin marketplace update oss-first-contribution
claude plugin update oss-first-contribution@oss-first-contribution
```

Restart Claude Code to apply the update.

## Codex plugin

```bash
codex plugin marketplace add Howardisme/oss-first-contribution
codex plugin add oss-first-contribution@oss-first-contribution
```

Start `codex`. The skill triggers automatically, or pick it from `/skills`.

**Update:**

```bash
codex plugin marketplace upgrade
codex plugin add oss-first-contribution@oss-first-contribution
```

### Codex: allow network access

Codex runs commands in a sandbox with networking off by default, and the analysis script needs to reach `api.github.com`. This applies whether you installed the plugin or copied the skill manually. Pick one:

- **Approve when asked.** In the default Auto mode, Codex asks before running a command that needs the network. Approve the `analyze_repo.py` commands.
- **Turn it on for all sessions.** Add this to `~/.codex/config.toml`:

  ```toml
  [sandbox_workspace_write]
  network_access = true
  ```

  Or enable it for a single session: `codex -c 'sandbox_workspace_write.network_access=true'`

**Pass your GitHub token.** If the script reports that no token was found (the sandbox may not be able to read `gh`'s credential store), export it before starting Codex:

```bash
export GITHUB_TOKEN="$(gh auth token)"     # macOS / Linux
```

```powershell
$env:GITHUB_TOKEN = (gh auth token)        # Windows (PowerShell)
```

## Manual installation

Use this for GitHub Copilot, or for Claude Code and Codex if you'd rather not use the plugin. Install the skill only one way per assistant (if you already installed the plugin, don't also copy the folder).

Clone the repository, then run the commands below from its root:

```bash
git clone https://github.com/Howardisme/oss-first-contribution.git
cd oss-first-contribution
```

Each assistant reads skills from its own folder:

| Assistant | Personal skills folder |
|---|---|
| Claude Code | `~/.claude/skills/` |
| Codex | `~/.agents/skills/` |
| GitHub Copilot | `~/.copilot/skills/` or `~/.agents/skills/` |

**macOS / Linux** (replace `~/.claude/skills` with the folder for your assistant):

```bash
mkdir -p ~/.claude/skills
rm -rf ~/.claude/skills/oss-first-contribution
cp -r skills/oss-first-contribution ~/.claude/skills/
ls ~/.claude/skills/oss-first-contribution/SKILL.md     # check
```

**Windows (PowerShell)** (replace `.claude\skills` with the folder for your assistant):

```powershell
New-Item -ItemType Directory -Force "$HOME\.claude\skills" | Out-Null
Remove-Item -Recurse -Force "$HOME\.claude\skills\oss-first-contribution" -ErrorAction SilentlyContinue
Copy-Item -Recurse "skills\oss-first-contribution" "$HOME\.claude\skills\"
Test-Path "$HOME\.claude\skills\oss-first-contribution\SKILL.md"    # check, should print True
```

Then:

- **Claude Code:** start `claude` and use `/oss-first-contribution`. If you created `~/.claude/skills` while Claude Code was running, run `/reload-skills` first.
- **Codex:** start `codex` and use `$oss-first-contribution`, or pick it from `/skills`. Remember to [allow network access](#codex-allow-network-access).
- **GitHub Copilot:** in VS Code, open Copilot Chat in **Agent** mode and type `/oss-first-contribution`. Copilot asks before running terminal commands, so approve the `analyze_repo.py` commands. If the skill doesn't show up, reload the window (**Developer: Reload Window**) and check **Chat: Open Customizations → Skills**.

**Update:** run `git pull` and repeat the copy commands above. They remove the old copy first, so files deleted upstream don't linger.
