# Changelog

All notable changes to this skill. Versions follow [SemVer](https://semver.org/):
MAJOR = structure/behaviour change, MINOR = new platform or section, PATCH = corrections.

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
