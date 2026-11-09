# Installing netconfig-skill

The skill is the folder [`skills/network-config/`](skills/network-config). It uses the open
[Agent Skills](https://agentskills.io/) format, so most AI coding agents can load it as-is.
Pick **one** of the three ways below.

| Way | Best for | Effort |
|---|---|---|
| [1. One-line installer](#1-one-line-installer) | Installing into every agent on your computer at once | One command |
| [2. Paste a prompt into your agent](#2-paste-a-prompt-into-your-agent) | Letting the agent install itself, from inside its own chat | Copy, paste, approve |
| [3. Per-agent instructions](#3-per-agent-instructions) | One specific agent, or a native install command | One command or a few clicks |

No AI agent at all? The **[NetConfig Assistant desktop app](app/README.md)** needs no install:
download the ZIP, open `app/` and double-click the start file.

After installing, **restart the agent** (or start a new chat) and check it with
[Verify it works](#verify-it-works).

---

## 1. One-line installer

### Option A: the `skills` CLI (any OS with Node.js)

[`npx skills`](https://github.com/vercel-labs/skills) knows the skills folder of about 80 agents
and asks which ones to install into:

```bash
npx skills add https://github.com/Lumax-Solutions/netconfig-skill/tree/main/skills/network-config -g
```

- `-g` installs for your user (all projects). Leave it out to install into the current project only.
- Add `-a '*' -y` to install into every supported agent without questions, or choose agents with
  `-a claude-code codex cursor gemini-cli github-copilot antigravity`.
- Update later with `npx skills update`, remove with `npx skills remove network-config -g`.
- The CLI sends anonymous usage telemetry; set `DISABLE_TELEMETRY=1` to turn it off.

### Option B: our install script (no Node.js needed)

It downloads the latest version and copies it into the shared `~/.agents/skills/` folder plus the
private folder of each agent it finds (Claude Code, Antigravity, Cline, Kiro, Trae, Continue). If it
finds Hermes Agent it installs there too, with `hermes skills install` when possible (see
[Hermes Agent](#hermes-agent)).

**Windows (PowerShell):**
```powershell
irm https://raw.githubusercontent.com/Lumax-Solutions/netconfig-skill/main/install.ps1 | iex
```

**macOS / Linux / WSL:**
```bash
curl -fsSL https://raw.githubusercontent.com/Lumax-Solutions/netconfig-skill/main/install.sh | bash
```

Options: `--project` / `-Project` (current project only), `--uninstall` / `-Uninstall`,
`--dry-run` / `-DryRun`, `--hermes-profile <name>` / `-HermesProfile <name>`,
`--no-hermes-cli` / `-NoHermesCli` (copy into Hermes instead of using `hermes skills install`). With options on Windows, download the script first:
`irm .../install.ps1 -OutFile install.ps1; .\install.ps1 -DryRun`. As with any script you pipe
into a shell, you can [read it first](install.ps1).

---

## 2. Paste a prompt into your agent

Works in any agent that can run shell commands and write files (Claude Code, Codex, Antigravity,
Cursor agent, Copilot agent mode, Gemini CLI, Cline, Roo, Kiro, OpenCode, Hermes, Goose, Amp,
Kilo, Trae, Qwen Code, Droid…). The agent will ask before running commands; approve them.

### Universal install prompt

Copy everything in the box into the agent’s chat:

```text
Install the "network-config" Agent Skill for me from GitHub.

Source: https://github.com/Lumax-Solutions/netconfig-skill (public, MIT). The skill is the folder
skills/network-config/ in that repo. Only install that folder; do not run any other code from the repo.

Steps:
1. Download the repo (git clone --depth 1, or download
   https://github.com/Lumax-Solutions/netconfig-skill/archive/refs/heads/main.zip) into a temporary folder.
2. Check that skills/network-config/SKILL.md exists and its frontmatter says "name: network-config".
3. Copy the whole skills/network-config folder (SKILL.md and references/, you can skip evals/) to my
   USER-level skills folder for THIS agent, so it works in every project. Use the path for this agent:
     Claude Code:         ~/.claude/skills/network-config
     Codex:               ~/.agents/skills/network-config
     Antigravity:         ~/.gemini/config/skills/network-config
     Gemini CLI:          ~/.gemini/skills/network-config
     Cursor:              ~/.cursor/skills/network-config
     GitHub Copilot:      ~/.copilot/skills/network-config
     Windsurf / Devin:    ~/.agents/skills/network-config
     Cline:               ~/.cline/skills/network-config
     Roo Code:            ~/.roo/skills/network-config
     Kilo Code:           ~/.kilo/skills/network-config
     Kiro:                ~/.kiro/skills/network-config
     OpenCode:            ~/.config/opencode/skills/network-config
     Hermes Agent:        $HERMES_HOME/skills/networking/network-config — if HERMES_HOME is not set:
                          ~/.hermes/skills/... (macOS/Linux/WSL), %LOCALAPPDATA%\hermes\skills\... (Windows).
                          If the `hermes` command works, prefer: hermes skills install
                          Lumax-Solutions/netconfig-skill/skills/network-config --category networking --force
     Trae:                ~/.trae/skills/network-config
     Qwen Code:           ~/.qwen/skills/network-config
     Factory Droid:       ~/.factory/skills/network-config
     Goose / Amp / other: ~/.agents/skills/network-config
   On Windows "~" means %USERPROFILE% (C:\Users\<me>). If you are not sure which agent you are or
   where your skills folder is, use ~/.agents/skills/network-config.
4. If a network-config folder already exists there, replace it (this is an update).
5. Delete the temporary folder, then tell me the exact path you installed to and whether I need to
   restart you or open a new chat for the skill to load.
```

### Short prompts for agents with a built-in installer

| Agent | Paste this |
|---|---|
| **Claude Code** | `/plugin marketplace add Lumax-Solutions/netconfig-skill` then `/plugin install netconfig@netconfig-skill` |
| **Codex** | `$skill-installer install https://github.com/Lumax-Solutions/netconfig-skill/tree/main/skills/network-config` |
| **Gemini CLI** | `Run: gemini skills install https://github.com/Lumax-Solutions/netconfig-skill.git --path skills/network-config --scope user --consent` |
| **Hermes Agent** | In the chat: `/skills install Lumax-Solutions/netconfig-skill/skills/network-config --category networking --force` (see [Hermes Agent](#hermes-agent) for why `--force`) |
| **Any agent with Node.js** | `Run: npx skills add https://github.com/Lumax-Solutions/netconfig-skill/tree/main/skills/network-config -g -y` and install it for yourself |

> **Can’t install by prompt:** Claude apps (claude.ai / Claude Desktop chat), Cursor Cloud Agents
> and other cloud-sandboxed agents can’t write to your computer’s skills folder. Use the upload or
> per-agent steps below.

---

## 3. Per-agent instructions

`~` = your home folder (`C:\Users\<you>` on Windows). **User** = all projects;
**Project** = commit it to one repo so your whole team gets it.

| Agent | User folder | Project folder | Native install |
|---|---|---|---|
| **Claude Code** | `~/.claude/skills/` | `.claude/skills/` | Plugin: `/plugin marketplace add Lumax-Solutions/netconfig-skill` then `/plugin install netconfig@netconfig-skill` (updates via `/plugin`), or copy the folder |
| **Claude apps** (claude.ai, Desktop) | — | — | Zip the `network-config` folder → *Customize → Skills → + → Upload a skill* |
| **OpenAI Codex** (CLI, IDE, app) | `~/.agents/skills/` | `.agents/skills/` | `$skill-installer` prompt (above) |
| **Google Antigravity** | `~/.gemini/config/skills/` | `.agents/skills/` | Copy the folder |
| **Gemini CLI** | `~/.gemini/skills/` or `~/.agents/skills/` | `.gemini/skills/` or `.agents/skills/` | `gemini skills install … --path skills/network-config` |
| **Cursor** | `~/.cursor/skills/` or `~/.agents/skills/` | `.cursor/skills/` or `.agents/skills/` | Copy the folder |
| **GitHub Copilot** (VS Code agent mode) | `~/.copilot/skills/` or `~/.agents/skills/` | `.github/skills/` or `.agents/skills/` | Copy the folder |
| **Windsurf / Devin Desktop** | `~/.agents/skills/` | `.agents/skills/` (or `.windsurf/skills/`) | Copy the folder |
| **Cline** | `~/.cline/skills/` | `.cline/skills/` | Copy the folder |
| **Roo Code** | `~/.roo/skills/` or `~/.agents/skills/` | `.roo/skills/` or `.agents/skills/` | Copy the folder |
| **Kilo Code** | `~/.kilo/skills/` or `~/.agents/skills/` | `.kilo/skills/` or `.agents/skills/` | Copy the folder |
| **Kiro** | `~/.kiro/skills/` | `.kiro/skills/` | IDE: *Agent Steering & Skills → + → Import a skill → GitHub* → paste `https://github.com/Lumax-Solutions/netconfig-skill/tree/main/skills/network-config` |
| **OpenCode** | `~/.config/opencode/skills/` | `.opencode/skills/` | Copy the folder |
| **Hermes Agent** | `~/.hermes/skills/` (Windows: `%LOCALAPPDATA%\hermes\skills\`; or `$HERMES_HOME/skills/`) | `.hermes/skills/` or `.agents/skills/`, after `hermes skills trust` in the repo (see [Hermes Agent](#hermes-agent)) | `hermes skills install Lumax-Solutions/netconfig-skill/skills/network-config --category networking --force` — see [Hermes Agent](#hermes-agent) |
| **Goose** | `~/.agents/skills/` | `.agents/skills/` | Copy the folder |
| **Amp** | `~/.config/agents/skills/` or `~/.agents/skills/` | `.agents/skills/` | `amp skill add` |
| **Trae** | `~/.trae/skills/` (Trae CN: `~/.trae-cn/skills/`) | `.trae/skills/` | Copy the folder |
| **Qwen Code** | `~/.qwen/skills/` or `~/.agents/skills/` | `.qwen/skills/` or `.agents/skills/` | Copy the folder |
| **Factory Droid** | `~/.factory/skills/` or `~/.agents/skills/` | `.factory/skills/` | Copy the folder |
| **Continue** | `~/.continue/skills/` (CLI) | `.continue/skills/` | Copy the folder (IDE support is partial) |

**Manual copy**, if you prefer: download
[the ZIP](https://github.com/Lumax-Solutions/netconfig-skill/archive/refs/heads/main.zip), unzip it,
and copy `skills/network-config` into the folder from the table, so you end up with
`<skills folder>/network-config/SKILL.md`.

### Hermes Agent

[Hermes Agent](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills) keeps skills in
its own folder and does **not** read `~/.agents/skills/` unless you add it (see the end of this
section).

**Recommended: install from GitHub with Hermes** (Hermes records where it came from, so
`hermes skills update` works):

```bash
hermes skills install Lumax-Solutions/netconfig-skill/skills/network-config --category networking --force
```

- **Why `--force`:** Hermes scans every skill from GitHub before installing. This skill's Linux
  examples contain `sudo` commands (`sudo ufw …`, `sudo nft …`), which the scanner rates
  *caution*, and Hermes blocks *caution* skills from community sources unless you pass `--force`.
  Nothing in the skill runs by itself: it's documentation that the model reads. To see the scan
  and the files before deciding, run
  `hermes skills inspect Lumax-Solutions/netconfig-skill/skills/network-config`.
- **From inside a Hermes chat:** `/skills install Lumax-Solutions/netconfig-skill/skills/network-config --category networking --force`
- **As a tap** (adds this repo as a skill source, then install by short name):
  ```bash
  hermes skills tap add Lumax-Solutions/netconfig-skill
  hermes skills install Lumax-Solutions/netconfig-skill/network-config --category networking --force
  ```
- **Rate limit:** Hermes uses the GitHub API, which allows 60 requests an hour without a login. If
  the install fails with a rate-limit error, put `GITHUB_TOKEN=<your token>` in `$HERMES_HOME/.env`
  (default `~/.hermes/.env`, or `%LOCALAPPDATA%\hermes\.env` on Windows) and try again.
- **Profiles:** each profile has its own skills folder (`$HERMES_HOME/profiles/<name>/skills`).
  Install into one with `hermes -p <profile> skills install … --category networking --force`.
- **Check:** start a new session (or `/reset`), then `hermes skills list` should show
  `network-config` in category `networking`.
- **Update:** `hermes skills update network-config`. **Remove:** `hermes skills uninstall network-config`.

**Or use our install script** (Option B above). It finds the Hermes home folder and, if the
`hermes` command works, runs the same command as above, once:
`hermes skills install … --category networking --yes --force`.

- `--force` only accepts the expected **caution** verdict (see above); after installing, the
  script says so in one line and points you to `hermes skills inspect`. One attempt keeps the
  GitHub API calls down (60 an hour without a token).
- If the scanner says **dangerous**, `--force` can't override it: the script stops with an error
  and installs nothing for Hermes. Please [open an issue](https://github.com/Lumax-Solutions/netconfig-skill/issues).
- For other failures (rate limit, offline, older Hermes) and when the `hermes` command isn't found,
  it copies the skill to `<Hermes home>/skills/networking/network-config` (without `evals/`).
  A copied skill is a *local* skill: `hermes skills update` won't update it. Re-run the script
  later (a rate limit resets within an hour) or after adding `GITHUB_TOKEN`, and it replaces the
  copy with an updatable hub install.
- `--no-force` / `-NoForce` runs the install without `--force`; a caution block then copies the
  skill instead.

Add `--hermes-profile <name>` / `-HermesProfile <name>` for a profile; `--dry-run` / `-DryRun`
shows the exact command and path first.

**Where Hermes keeps skills:** `$HERMES_HOME/skills/`. If `HERMES_HOME` isn't set:
`~/.hermes/skills/` on macOS, Linux and WSL, and **`%LOCALAPPDATA%\hermes\skills\` on native
Windows** (not `%USERPROFILE%\.hermes`). Skills can sit one level down in a category folder, so
both `skills/network-config/` and `skills/networking/network-config/` work. Older versions of our
script copied the skill to `%USERPROFILE%\.hermes\skills\network-config` on Windows, where
Hermes doesn't look; `-Uninstall` removes that copy.

**Project skills (for a team repo):** per the Hermes docs, Hermes also loads skills committed to
a repo in `<repo>/.hermes/skills/` or `<repo>/.agents/skills/`, but only after you trust that
repo: run `hermes skills trust` inside the checkout (or `hermes skills trust <path>`), and
`hermes skills untrust` to revoke. Trust is per project; it isn't needed for taps or for skills
installed with `hermes skills install`. The command isn't in hermes-agent 0.19.0 (the latest on
PyPI in November 2026), so check `hermes skills --help` for it on your version.

**Prefer one shared folder?** Hermes can also read `~/.agents/skills/` (where the install script
puts the skill for other agents) if you add it to `config.yaml`:

```yaml
skills:
  external_dirs:
    - ~/.agents/skills
```

### Agents without skill support

Use the single-file build [`dist/AGENTS.md`](dist/AGENTS.md) as a rules file or system prompt:
`.cursor/rules/`, `.github/copilot-instructions.md`, `.windsurf/rules/`, `.clinerules/`,
`AGENTS.md`, `GEMINI.md`, Open WebUI / LM Studio / Ollama system prompt. For small local models,
build a smaller file with only the platforms you use:

```bash
python scripts/build_agents_md.py --only fortigate,cisco-ios --out my-network-prompt.md
```

---

## Verify it works

1. Restart the agent or open a new chat.
2. Ask: **“Which skills do you have?”** — `network-config` should be listed. (Some agents have a
   command instead: `/skills` in Claude Code and Codex, `gemini skills list`, `hermes skills list`.)
3. Try: **“Write a FortiGate 7.4 port forward for 192.168.1.50:443 on wan1.”** A working install
   answers with *Assumptions → Pre-checks/backup → Configuration → Verification → Rollback*.

## Update and uninstall

- `npx skills update` / `npx skills remove network-config -g` if you used the `skills` CLI.
- Re-run the install script to update; add `--uninstall` / `-Uninstall` to remove.
- Hermes: `hermes skills update network-config` / `hermes skills uninstall network-config` if
  installed with `hermes skills install`; copies made by the script are removed by `--uninstall`.
- Manual installs: replace or delete the `network-config` folder.

## Troubleshooting

| Problem | Fix |
|---|---|
| Skill not listed | Check the path ends in `network-config/SKILL.md` (not `network-config/network-config/…` or `skills/network-config/skills/…`). Restart the agent. |
| Agent lists it twice | Some agents read both `~/.agents/skills/` and their own folder. Harmless; delete one copy if it bothers you. |
| Hermes: "Installation blocked … caution verdict" | Expected: the scanner flags the `sudo` examples. Review with `hermes skills inspect …`, then add `--force` (see [Hermes Agent](#hermes-agent)). |
| Hermes: rate-limit error | Wait for the limit to reset (within an hour) or add `GITHUB_TOKEN=<token>` to `$HERMES_HOME/.env`, then retry. If the install script copied the skill instead, re-running it switches to a hub install. |
| Hermes ignores a skill committed to a repo | Project skills load only from a trusted repo: run `hermes skills trust` in the checkout (see [Hermes Agent](#hermes-agent)). |
| Hermes doesn't list it | It doesn't read `~/.agents/skills/`. Check `<Hermes home>/skills/networking/network-config/SKILL.md` exists (Windows: under `%LOCALAPPDATA%\hermes`), then start a new session. |
| Claude app upload rejected | The ZIP must contain the `network-config` folder at its top level, and *Code execution* must be on in settings. |
| Corporate proxy blocks downloads | Download the ZIP in your browser and copy the folder manually. |
| Agent can’t run the install prompt | It has no shell or file access (cloud/sandboxed). Use option 1 or 3 on your own computer. |

Paths come from each vendor’s documentation as of November 2026 and do change. If one is wrong,
please [open an issue](https://github.com/Lumax-Solutions/netconfig-skill/issues/new/choose).
