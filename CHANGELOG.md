# Changelog

All notable changes to this skill. Versions follow [SemVer](https://semver.org/):
MAJOR = structure/behaviour change, MINOR = new platform or section, PATCH = corrections.

## [1.0.0] — 2026-11-07

### Added
- Core `SKILL.md` (workflow, safety rules, vendor detection, cross-vendor concept map,
  lockout-prevention checklist, troubleshooting method) with per-platform reference files:
  Cisco IOS/IOS-XE, NX-OS, ASA/FTD, FortiGate, Palo Alto, Juniper, MikroTik, Check Point,
  Huawei, Aruba/HPE, Arista, SonicWall/VyOS/pfSense/Sophos/UniFi, host & cloud firewalls.
- Config audit checklist and cross-vendor migration guide.
- 7 evaluation cases (`network-device-config/evals/`) in the `claude plugin eval` layout.
- `scripts/build_agents_md.py` single-file build (`dist/AGENTS.md`) for tools without skill support.
- `scripts/validate.py` and a GitHub Actions workflow.

### Verified
- 37 version-sensitive claims checked against official vendor documentation (November 2026), including:
  FortiOS IKE debug syntax change at 7.4.1, SSL-VPN tunnel mode removal in 7.6.3, SD-WAN rename in 6.4.1,
  static-NAT VIP outbound SNAT behaviour, Cisco SVTI "any any" selectors, ISR HSEC limits,
  MikroTik RouterOS 7.20 BGP instances, Junos default (non-RFC 8212) BGP behaviour,
  Palo Alto Expedition end-of-life.
