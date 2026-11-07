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
private folder of each agent it finds (Claude Code, Antigravity, Cline, Kiro, Trae, Hermes, Continue).

**Windows (PowerShell):**
```powershell
irm https://raw.githubusercontent.com/Lumax-Solutions/netconfig-skill/main/install.ps1 | iex
```

**macOS / Linux / WSL:**
```bash
curl -fsSL https://raw.githubusercontent.com/Lumax-Solutions/netconfig-skill/main/install.sh | bash
```

Options: `--project` / `-Project` (current project only), `--uninstall` / `-Uninstall`,
`--dry-run` / `-DryRun`. With options on Windows, download the script first:
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
     Hermes Agent:        ~/.hermes/skills/network-config
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
| **Hermes Agent** | `Run: hermes skills install Lumax-Solutions/netconfig-skill/skills/network-config` |
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
| **Hermes Agent** | `~/.hermes/skills/` | `.hermes/skills/` (then `hermes skills trust`) | `hermes skills install Lumax-Solutions/netconfig-skill/skills/network-config` |
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
- Manual installs: replace or delete the `network-config` folder.

## Troubleshooting

| Problem | Fix |
|---|---|
| Skill not listed | Check the path ends in `network-config/SKILL.md` (not `network-config/network-config/…` or `skills/network-config/skills/…`). Restart the agent. |
| Agent lists it twice | Some agents read both `~/.agents/skills/` and their own folder. Harmless; delete one copy if it bothers you. |
| Project skill ignored (Hermes, some IDEs) | Project-level skills may need to be trusted first, e.g. `hermes skills trust`. |
| Claude app upload rejected | The ZIP must contain the `network-config` folder at its top level, and *Code execution* must be on in settings. |
| Corporate proxy blocks downloads | Download the ZIP in your browser and copy the folder manually. |
| Agent can’t run the install prompt | It has no shell or file access (cloud/sandboxed). Use option 1 or 3 on your own computer. |

Paths come from each vendor’s documentation as of November 2026 and do change. If one is wrong,
please [open an issue](https://github.com/Lumax-Solutions/netconfig-skill/issues/new/choose).
