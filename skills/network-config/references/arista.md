# Arista — EOS

Part of the `network-config` skill. Read `../SKILL.md` first for the workflow and safety rules.

## Arista EOS

IOS-like. Notes: L3 needs `ip routing`; routed ports need `no switchport`; masks may be /len.
Use config sessions for safety: `configure session CHG1` → changes → `show session-config diffs` → `commit timer 00:05:00` (auto-rollback if not confirmed) → `configure session CHG1 commit` to confirm.
MLAG: `mlag configuration` → `domain-id`, `local-interface Vlan4094`, `peer-address`, `peer-link Port-Channel10`. BGP: `router bgp 65001` → `neighbor X remote-as Y` → `network ...`.
Show: `show ip bgp summary`, `show mlag`, `show interfaces status`, `bash tcpdump -i et1`.
