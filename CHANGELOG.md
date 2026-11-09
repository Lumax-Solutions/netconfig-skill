# Changelog

All notable changes to this skill. Versions follow [SemVer](https://semver.org/):
MAJOR = structure/behaviour change, MINOR = new platform or section, PATCH = corrections.

## [1.4.1] — 2026-11-09

Theme: first-class Hermes Agent support.

### Added
- **Hermes Agent in the install scripts** (`install.sh`, `install.ps1`):
  - Finds the Hermes home as `$HERMES_HOME`, else `%LOCALAPPDATA%\hermes` on native Windows (a
    legacy `%USERPROFILE%\.hermes` only if it has a `config.yaml`), else `~/.hermes`
    (macOS, Linux, WSL). Detects Hermes when that folder exists or `hermes` is on PATH.
  - Runs `hermes skills install Lumax-Solutions/netconfig-skill/skills/network-config --category
    networking --yes --force` once, so `hermes skills update` works, and reads the result (Hermes
    can exit 0 without installing). `--force` accepts the expected **caution** verdict, explained
    in one line after the install; Hermes never lets it override **dangerous**, which stops the
    script with an error and nothing copied. A single attempt halves the GitHub API calls (60/hour
    without a token). Other failures (rate limit, offline, older Hermes) fall back to copying the
    skill to `<Hermes home>/skills/networking/network-config` without `evals/`; the message says a
    rate limit resets within an hour and that re-running (or adding `GITHUB_TOKEN`) switches the
    copy to an updatable hub install.
  - New options: `--hermes-profile` / `-HermesProfile`, `--no-force` / `-NoForce` (install
    without `--force`; a caution block copies instead), `--no-hermes-cli` / `-NoHermesCli`,
    `--source` / `-Source` (install from a local checkout). `--uninstall` uses
    `hermes skills uninstall` for hub installs and also removes the copy that older versions put in
    `%USERPROFILE%\.hermes\skills` on Windows. `--dry-run` shows the exact command and path.
- **SKILL.md metadata for Hermes:** `metadata.author`, `metadata.hermes.category: networking` and
  `metadata.hermes.tags`. Kept under `metadata` because the Agent Skills spec (and its `skills-ref`
  validator) rejects extra top-level keys such as `author`; `scripts/validate.py` now enforces that
  and checks that SKILL.md and `plugin.json` versions match.
- **INSTALL.md "Hermes Agent" section:** one-liner, tap, `/skills install` in a chat, the
  `GITHUB_TOKEN` rate-limit fix, profiles, update/uninstall, the Windows path, and
  `skills.external_dirs` for people who prefer `~/.agents/skills`. README: Hermes one-liner.
- **CI job "Hermes Agent install":** 109 offline installer checks for both scripts (a stub `hermes` covers caution, dangerous,
  rate-limit and re-run results) (pwsh on Ubuntu,
  Windows paths simulated), the real Hermes 0.19.0 CLI listing the copied skill in category
  `networking`, Hermes' security scanner run on the whole skill folder, `evals/` included (the job fails on *dangerous*; *caution* is expected), and on `main`
  a real `hermes skills install … --force` from GitHub, `hermes skills list` and uninstall.

### Tested on real machines
- Windows, PowerShell 5.1, Hermes 0.20.5: Hermes path, DANGEROUS abort (against the old main),
  copy install without `evals/`, uninstall of both copies, nothing written to `%USERPROFILE%\.hermes`;
  a token-less run hit GitHub's rate limit and fell back to the copy, which led to the single
  `--force` attempt above.
- Linux, Hermes 0.19.0: `install.sh` against the pushed main ended as a hub install
  (`scan_verdict: caution`).

### Changed
- `references/host-cloud.md` and `ipv6.md`: persist iptables rules with `netfilter-persistent save`
  (Debian/Ubuntu; RHEL: `service iptables save`) instead of `iptables-save > /etc/iptables/rules.v4`.
  Same result; Hermes' scanner rated the redirect into `/etc` *critical*, which blocks installation
  even with `--force`.

### Fixed (from an independent review of the skill)
- **Juniper:** the example ran `commit confirmed 5` and `commit` in the same paste, which confirms
  at once and defeats the automatic rollback. It now stops after `commit confirmed 5`, says what to
  test from a new session, and confirms with `commit` as a separate step.
- **Juniper BGP example** now matches its own advice: a `discard` static route anchors the
  advertised prefix (before, nothing would have been advertised), the export policy matches
  `protocol static` + a prefix list and rejects the rest, and there is an import policy and an
  `accepted-prefix-limit`; on an SRX the zones now allow BGP and OSPF to reach the device. It
  explains that the static default outranks the BGP default and how to switch, and how to size the
  prefix limit for a full table.
- **Paste blocks:** comment-only `# …` lines moved out of device paste blocks (Juniper, Palo Alto,
  FortiGate troubleshooting); Check Point's clish and `mgmt_cli` commands, which run in different
  shells, are now separate blocks. `validate.py` now fails on `#` lines in device paste blocks and
  on any other `commit …` (plain, `and-quit`, `comment`, `synchronize`) in the same block as
  `commit confirmed`.
- **Coverage labels:** Palo Alto and Juniper moved from *Detailed* to *Standard* (they have no full
  IPsec/HA/GlobalProtect examples yet), so answers for them include the "verify on your device" note.
- An eval grader (`mikrotik-vlan-guest/graders/09-check.md`) was worded "do not tell the user to
  reconnect via MAC-winbox…", which Hermes' scanner flags as *critical* (deception), making the
  full skill folder *dangerous*. Reworded to "they must not rely on reconnecting via MAC-winbox…";
  the grader checks the same thing.
- Hermes paths in INSTALL.md: the old table pointed Windows users to `%USERPROFILE%\.hermes`.
  `hermes skills trust` is now documented for what it does (trusting a repo so its own
  `.hermes/skills/` / `.agents/skills/` load), not as an install step. The scripts no longer claim
  Hermes reads `~/.agents/skills`.
- `dist/AGENTS.md` still told the model to "read the reference file(s)" although every reference
  is included inline: the build's text replacement stopped matching after the SKILL.md wording
  changed in 1.3.0. The build now matches across line breaks, also rewrites the "syntax lives in
  `references/`" sentence, and **fails** if a rewrite no longer matches or the instruction remains,
  so CI catches it. Reported by a Hermes Agent review.

## [1.4.0] — 2026-11-08

Theme: a desktop app for people who don't use AI agents. The skill's own content is unchanged from
1.3.0; the version moves with the release.

### Added
- **NetConfig Assistant** (`app/`): a guided desktop app for people new to networking. A local
  web UI (Python standard library only, no install) with a three-step wizard (device → task →
  details), streamed answers with Copy buttons, follow-up chat and Markdown export.
  - AI: any OpenAI-compatible server (llama.cpp/llama-swap, Ollama, LM Studio, vLLM, OpenAI,
    DeepInfra …) or the Anthropic API; detects local servers automatically.
  - Sends the core skill plus only the matching reference files, so local models without tool use
    get the right material; guesses the vendor from a pasted config when the user picks "Not sure".
  - Removes passwords, keys and SNMP communities from pasted configs on the user's computer (with a
    report of what was removed); optional public-IP masking.
  - Advice only: never connects to devices. Listens on 127.0.0.1 and refuses other origins.
  - `app/test_app.py` (31 offline checks) runs in CI.
  - User guide with screenshots (`app/README.md`): install, AI setup, each step, reading the
    answer, privacy, troubleshooting, FAQ.
  - Works with models that reject optional settings: drops `temperature` (newer Claude models)
    or switches to `max_completion_tokens` (OpenAI reasoning models) and retries automatically.
  - `scripts/build_app_zip.py` builds `NetConfig-Assistant.zip` (app + skill, start files at the
    top level) for releases.

## [1.3.0] — 2026-11-07

Theme: claims you can trace, and advice proven in a lab.

### Added
- **`SOURCES.md`:** 53 version-sensitive claims, each with its vendor source, the versions it
  applies to, status (38 verified, 8 corrected, 7 unverified) and a last-checked date. Every
  source was re-fetched and checked against the page text.
- **Freshness check:** `scripts/validate.py` checks `SOURCES.md` rows and warns in CI when a source
  is over 12 months old.
- **Linux firewall lab** (`tests/lab/`), run in CI on every push over IPv4 and IPv6:
  - *SSH-lockdown demo:* the skill's own answer to "restrict SSH to the admin host, keep the website
    up, don't lock me out", copied verbatim, is applied to a disposable server and tested from
    separate clients — existing session survives, admin allowed, others blocked, web open, the
    rollback timer restores access when not confirmed, and the confirmed change persists.
  - *Reference examples:* the nftables and iptables examples in `host-cloud.md` are loaded and
    tested the same way.
- **Claude Code plugin:** `/plugin marketplace add Lumax-Solutions/netconfig-skill` then
  `/plugin install netconfig@netconfig-skill` (validated with `claude plugin validate`).
- **"Share a test case" issue template** for real-world cases that become regression tests.
- `tests/codex/`: the independent Codex test kit (answer-quality and activation harnesses, cases,
  rubric, results and sample answers).
- README: the lab demo and a "knows when to stop" FortiGate example up front; independent test results.

### Fixed (from re-checking sources)
- Cisco: `archive` is **required** (not just recommended) for `configure terminal revert timer`;
  softened the undocumented claim about IKEv2 policies replacing the smart-default policy.
- FortiGate: IPv4+IPv6 in one policy since **6.4.0** (not "7.x"); "any" VIP outbound SNAT wording.
- Palo Alto: PAN-OS 11.1+ Panorama-managed firewalls have Automated Commit Recovery.
- Huawei `commit trial` and Arista session-confirm details now marked "verify with `?`".

### Release check (independent, Codex CLI)
- Answer quality 20/20 (baseline 19/20); activation 8/8 relevant and 0/4 controls; the VPN
  troubleshooting case now loads the FortiGate and Cisco references; 3 SOURCES.md rows spot-checked.
- MikroTik: noted that Safe Mode exits (and stops protecting) when a change exceeds its history
  capacity — found during the source spot-check.

### Changed
- Agents read the platform reference files for troubleshooting too, not only before writing config
  (an independent activation test showed a VPN troubleshooting request loading only the core).

## [1.2.1] — 2026-11-07

### Fixed (found by an independent Codex smoke test)
- FortiGate `match-vip`: the reference said deny policies default to `disable` in 7.x. Correct:
  disabled up to 7.2.3; from 7.2.4 new deny policies default to `enable`, and policies carried
  over by an upgrade keep their previous value. The skill now tells the agent to check the actual
  setting (`show full-configuration firewall policy <id> | grep match-vip`) instead of assuming,
  and cites the FortiOS 7.2.4 release notes (bug 819937).
- Added a regression check for this to the `fortigate-existing-publish-server` eval case.

## [1.2.0] — 2026-11-07

Focus: safe changes to existing networks (based on an external review).

### Added
- **Existing-device change workflow** in the core: collect state (read-only) → minimal
  Add/Modify/Remove diff with conflict checks → prepare recovery → apply in phases → acceptance
  test (allowed *and* blocked traffic) → save after verification. Quick questions and greenfield
  builds skip the parts they don't need.
- `references/change-workflow.md`: read-only state commands per vendor, conflict checks (name/ID
  clashes, shadowing, overlaps, NAT mode, references, HA), a running-vs-saved recovery table for
  11 platforms, phasing rules and the acceptance-matrix template.
- `references/ipv6.md`: dual-stack checklist and IPv6 configs for Cisco, FortiGate, Palo Alto,
  Junos, MikroTik and Linux.
- `references/sanitizing-configs.md`: how to redact secrets while keeping a config diagnosable,
  and where secrets hide per vendor.
- Coverage depth labels (Detailed / Standard / Brief) per platform.
- FortiGate `match-vip` behaviour, explicit-ID policy placement; Cisco IKEv2 policy side effects,
  PSK `?` pitfall, licence reload, per-peer IKEv2 debugging.
- Eval case `fortigate-existing-publish-server` with planted conflicts; extra assertions on
  rollback timing and blocked-traffic tests.

### Changed
- Output format: one assumptions/conflicts table, change plan only for brownfield edits, recovery
  in three bullets, acceptance matrix of about six rows; management-adjacent edits always under an
  armed rollback with saving only after confirmation.
- Removed absolute safety wording ("never cut off").

### Test results
- Existing-device FortiGate change: v1.2 10/10 vs v1.1 4/8 on the original checks.
- FortiGate↔Cisco IPsec: v1.2 10/10 vs v1.1 7/8; v1.1 edited the WAN ACL before arming the
  rollback timer, v1.2 does not.
- After tightening, answers are ~1.1× the length of v1.1's instead of ~1.6×.

## [1.1.0] — 2026-11-07

### Fixed (from an external review)
- Unknown OS version on a live device: the skill now asks for the version (and gives the command
  that shows it) before writing commands, instead of assuming the mainstream release.
- iptables example now adds the allow rules before `-P INPUT DROP`, with an armed rollback,
  matching the skill's own lockout-prevention rules.

### Changed
- Skill moved to `skills/network-config/`, the standard location that cross-agent installers
  (`npx skills`, Hermes, Gemini CLI) discover automatically.

### Added
- `INSTALL.md`: install guide for Claude Code, Claude apps, Codex, Antigravity, Gemini CLI, Cursor,
  GitHub Copilot, Windsurf/Devin, Cline, Roo, Kilo, Kiro, OpenCode, Hermes, Goose, Amp, Trae, Qwen Code,
  Factory Droid and Continue, plus a copy-paste prompt that lets an agent install the skill itself.
- `install.ps1` (Windows) and `install.sh` (macOS/Linux): one-line installers that copy the skill into
  `~/.agents/skills` and each detected agent's own skills folder; `--project`, `--uninstall`, `--dry-run`.

## [1.0.0] — 2026-11-07

### Added
- Core `SKILL.md` (workflow, safety rules, vendor detection, cross-vendor concept map,
  lockout-prevention checklist, troubleshooting method) with per-platform reference files:
  Cisco IOS/IOS-XE, NX-OS, ASA/FTD, FortiGate, Palo Alto, Juniper, MikroTik, Check Point,
  Huawei, Aruba/HPE, Arista, SonicWall/VyOS/pfSense/Sophos/UniFi, host & cloud firewalls.
- Config audit checklist and cross-vendor migration guide.
- 7 evaluation cases (`network-config/evals/`) in the `claude plugin eval` layout.
- `scripts/build_agents_md.py` single-file build (`dist/AGENTS.md`) for tools without skill support.
- `scripts/validate.py` and a GitHub Actions workflow.

### Verified
- 37 version-sensitive claims checked against official vendor documentation (November 2026), including:
  FortiOS IKE debug syntax change at 7.4.1, SSL-VPN tunnel mode removal in 7.6.3, SD-WAN rename in 6.4.1,
  static-NAT VIP outbound SNAT behaviour, Cisco SVTI "any any" selectors, ISR HSEC limits,
  MikroTik RouterOS 7.20 BGP instances, Junos default (non-RFC 8212) BGP behaviour,
  Palo Alto Expedition end-of-life.
