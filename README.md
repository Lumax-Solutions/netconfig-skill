# netconfig-skill

An **Agent Skill** that turns an AI coding/chat agent into a careful senior network engineer for
routers, switches and firewalls — it writes paste-ready configs, reviews/audits configs, reads
`show`/`debug` output, and converts configs between vendors, **with backup, verification and
rollback steps built in** so you don't lock yourself out of a remote box.

| Area | Platforms |
|---|---|
| Cisco | IOS / IOS-XE (ISR, ASR, Catalyst, C8000v), NX-OS (Nexus), ASA, Firepower FTD |
| Firewalls | Fortinet FortiGate (FortiOS 6.4–7.6), Palo Alto PAN-OS, Check Point Gaia, Huawei USG, SonicWall, Sophos, pfSense/OPNsense |
| Routing / switching | Juniper Junos (SRX, MX, EX/QFX), MikroTik RouterOS v7, Huawei VRP, Aruba/HPE AOS-CX, Arista EOS, VyOS/EdgeOS |
| Host & cloud | UFW, nftables, iptables, Windows Defender Firewall, AWS SG/NACL, Azure NSG, GCP firewall rules, Kubernetes NetworkPolicy |

Topics: interfaces, VLANs/trunks/LACP, static/OSPF/BGP, ACLs and firewall policies, NAT/PAT/VIPs,
site-to-site IPsec (IKEv2, route-based), SD-WAN, HA, hardening, audits, cross-vendor migration,
troubleshooting.

> **Disclaimer.** This skill produces suggestions, not guarantees. Always review generated
> configuration, test in a lab or maintenance window, keep out-of-band access, and verify
> version-specific syntax on your device (`?` / tab completion). You are responsible for changes
> made to your equipment. Vendor and product names are trademarks of their respective owners;
> this project is not affiliated with or endorsed by any vendor.

---

## What makes it different from asking an LLM directly

- **Built for changing live networks.** For an existing device it follows a change workflow:
  collect the current state with read-only commands → propose a minimal Add/Modify/Remove diff and
  flag conflicts (name clashes, shadowing rules, overlapping VIPs/NAT) → arm the platform's
  automatic rollback (`configure revert timer`, `commit confirmed`, Safe Mode, `checkpoint auto` …)
  → apply in phases → test what must work **and** what must stay blocked → save only after it passes.
  It knows what each rollback restores (running vs saved config) on 11 platforms.
- **Proportional.** Quick questions get quick answers; greenfield builds skip the state collection.
- **Version-aware.** Known syntax changes are spelled out (e.g. FortiOS IKE debug filter changed in
  7.4.1, SSL-VPN tunnel mode removed in 7.6.3, RouterOS 7.20 BGP instances, PAN-OS advanced
  routing engine, VyOS 1.4 firewall syntax).
- **Encodes the gotchas that break production:** Cisco VTI "any/any" selectors vs FortiGate phase 2,
  FortiGate VIP-as-dstaddr and post-DNAT service ports, PAN-OS pre-NAT IP / post-NAT zone and U-turn
  NAT, ASA security-level implicit permits during migrations, stateless WAN ACLs that break PAT
  return traffic, Junos BGP not being RFC 8212-safe by default, `no-readvertise` killing exports,
  MikroTik bridge VLAN filtering lockouts, Docker bypassing UFW …
- **IPv6 and dual-stack aware**, with a checklist for the classic gap: IPv4 locked down, IPv6 wide open.
- **Small context footprint.** A ~220-line core plus one reference file per platform, loaded only
  when needed.

## Test results

Answers were generated with and without the skill on the same prompts, then graded against
objective checks and reviewed by a separate model acting as a senior network engineer
(November 2026). Cases live in [`skills/network-config/evals/`](skills/network-config/evals).

| Case | Without skill | With skill | Notable difference found in review |
|---|---|---|---|
| FortiGate ↔ Cisco ISR IPsec (remote change) | 7/7 | 7/7 | Skill: correct 7.4 debug syntax, Null0 anti-leak route on Cisco |
| ASA → FortiGate migration | 7/8 | 8/8 | Baseline: wrong hairpin advice, no backup/rollback |
| Cisco router security audit | 9/9 | 9/9 | Baseline: proposed WAN ACL breaks PAT return UDP, no auto-rollback |
| MikroTik VLANs + guest isolation | 7/7 | 7/7 | Early skill version missed NAT and had a rule-order slip (fixed) |
| Palo Alto DNAT + U-turn | 6/7 | 7/7 | Baseline: no validate/backup/rollback, no default-vwire warning |
| FortiGate debug-flow diagnosis | 6/6 | 6/6 | Both correct |
| Juniper SRX BGP (prompt in Arabic) | 7/8 | 8/8 | Baseline: `no-readvertise` blocks the advertisement, possible SSH lockout, wrong rollback number |

**v1.2 vs v1.1** (existing-device changes, November 2026):

| Case | v1.1 | v1.2 | Difference |
|---|---|---|---|
| Change a live FortiGate with planted conflicts (busy VIP port, name clash, deny rule above) | 4/8 | 10/10 | v1.1: no diff, single paste, no blocked-traffic test |
| FortiGate ↔ Cisco IPsec, remote | 7/8 | 10/10 | v1.1 edited the Cisco WAN ACL before arming the rollback timer |

The checklists alone don't separate the two well; the real gap is in **errors that would break
traffic or lock you out**, which the skill avoided and the baseline didn't. Treat these as a small
sample, not a guarantee.

## Platform coverage

| Depth | Platforms |
|---|---|
| **Detailed** (full syntax, version notes, tested scenarios) | Cisco IOS/IOS-XE, Cisco ASA, FortiGate, Palo Alto PAN-OS, Juniper Junos, MikroTik RouterOS |
| **Standard** (core syntax and troubleshooting) | Cisco NX-OS, Check Point, Huawei VRP/USG, Aruba AOS-CX, Linux / Windows / cloud firewalls |
| **Brief** (pointers; verify on the device) | Cisco FTD, Arista EOS, SonicWall, VyOS/EdgeOS, pfSense/OPNsense, Sophos, UniFi |

## Install

**Quickest** — installs into every agent on your computer (Claude Code, Codex, Cursor, Copilot,
Antigravity, Gemini CLI, Windsurf, Cline, Roo, Kiro, OpenCode, Hermes and more):

```powershell
# Windows (PowerShell)
irm https://raw.githubusercontent.com/Lumax-Solutions/netconfig-skill/main/install.ps1 | iex
```
```bash
# macOS / Linux
curl -fsSL https://raw.githubusercontent.com/Lumax-Solutions/netconfig-skill/main/install.sh | bash
# or, with Node.js, pick agents interactively:
npx skills add https://github.com/Lumax-Solutions/netconfig-skill/tree/main/skills/network-config -g
```

**From inside your agent** — paste the install prompt from [INSTALL.md](INSTALL.md#2-paste-a-prompt-into-your-agent)
and the agent installs the skill itself.

**Claude apps (claude.ai / Desktop)** — zip `skills/network-config` and upload it under
*Customize → Skills*.

**Any other tool or local model** — use the single-file build [`dist/AGENTS.md`](dist/AGENTS.md)
as a rules file or system prompt.

Per-agent paths, native install commands, verification and troubleshooting:
**[INSTALL.md](INSTALL.md)**.

## Example prompts

- "Site-to-site IPsec between our FortiGate 100F (7.4) and a Cisco ISR 4331 (IOS-XE 17.9). I'm doing the Cisco side remotely."
- "Convert this ASA config to FortiGate 7.2" *(paste config)*
- "Audit this router config for security issues" *(paste config)*
- "Port forward isn't working, here's `diagnose debug flow`" *(paste output)*
- "MikroTik hAP ax3: staff and guest VLANs, guest isolated, I'm connected on ether5."
- "عايز أعمل BGP مع مزود الخدمة على Juniper SRX300" — works in any language.

## Repository layout

```
skills/network-config/        ← the skill (copy this folder)
├── SKILL.md                  core workflow, safety rules, vendor detection, concept map
├── references/               one file per platform + change workflow, IPv6, sanitizing, audit, migration
└── evals/                    test cases (prompt.md, case.yaml, graders/)
INSTALL.md                    installation guide for every agent
install.ps1 / install.sh      one-line installers
dist/AGENTS.md                single-file build for non-skill tools (generated)
scripts/validate.py           structure / link / paste-safety checks (run in CI)
scripts/build_agents_md.py    builds dist/AGENTS.md
```

## Running the evaluations

Each case under `skills/network-config/evals/` contains the user prompt and one grader file per
check. With Claude Code ≥ 2.1.269 you can run them with and without the skill:

```bash
cd skills/network-config
claude plugin eval . --allow-tools Write,Edit,Bash
```

These are real, billed model runs. Without Claude Code, run the prompts in any agent with and
without the skill and grade answers against the `graders/` files by hand.

## Contributing

Corrections from people running this gear are very welcome — please include the OS version and a
vendor doc link. See [CONTRIBUTING.md](CONTRIBUTING.md). Report wrong commands with the
"Wrong or outdated command" issue template.

## License

[MIT](LICENSE)
