# SonicWall, VyOS/EdgeOS, pfSense/OPNsense, Sophos, UniFi

Part of the `network-config` skill. Read `../SKILL.md` first for the workflow and safety rules.

## Others (brief)

- **SonicWall (SonicOS 7):** primarily GUI (Objects → Address Objects; Policy → Rules and Policies → Access Rules / NAT Rules; Network → IPsec VPN). SonicOS 7 has a CLI with `configure` and `commit`, but syntax varies by firmware — give GUI steps and say to verify CLI with `?`. Troubleshoot: Packet Monitor, Connections Monitor, `diag` pages.
- **VyOS / Ubiquiti EdgeOS:** `configure` → `set interfaces ethernet eth0 address 203.0.113.2/30` → `set protocols static route 0.0.0.0/0 next-hop 203.0.113.1` → NAT `set nat source rule 100 outbound-interface name eth0` (VyOS 1.4; 1.3/EdgeOS: `outbound-interface eth0`) `source address 10.0.0.0/24` `translation address masquerade` → `commit` → `save`. VyOS 1.4 firewall moved to `set firewall ipv4 forward filter rule ...`; EdgeOS/VyOS 1.3 use named rulesets applied to interfaces. Safety: `commit-confirm 5` then `confirm` within 5 minutes.
- **pfSense / OPNsense:** GUI-driven (Firewall → Rules per interface, first match wins, inbound on the interface the traffic enters; Firewall → NAT → Port Forward/Outbound). Config is `/conf/config.xml`. Shell diagnostics: `pfctl -sr` (rules), `pfctl -ss` (states), `tcpdump -ni em0 host 10.0.0.5`. Backup: Diagnostics → Backup & Restore.
- **Sophos Firewall (SFOS):** GUI/API for rules & NAT (since v18 NAT rules are separate from firewall rules); console has `system diagnostics` and `tcpdump 'host 10.0.0.5'`, `conntrack -L`.
- **Ubiquiti UniFi:** controller-managed; give UI steps, not CLI.
