# Juniper — Junos (SRX, MX, EX/QFX)

Part of the `network-config` skill. Read `../SKILL.md` first for the workflow and safety rules.

## Juniper Junos (SRX, MX, EX/QFX)

Base, zones, policy and NAT. Junos changes go to the candidate config and only take effect on
`commit`; `commit confirmed 5` activates them and rolls back automatically after 5 minutes unless
you confirm:
```
configure
set system host-name SRX1
set system services ssh root-login deny
set interfaces ge-0/0/0 unit 0 family inet address 203.0.113.2/30
set interfaces ge-0/0/1 unit 0 family inet address 10.0.0.1/24
set routing-options static route 0.0.0.0/0 next-hop 203.0.113.1
set security zones security-zone untrust interfaces ge-0/0/0.0 host-inbound-traffic system-services ike
set security zones security-zone trust interfaces ge-0/0/1.0 host-inbound-traffic system-services ping
set security zones security-zone trust interfaces ge-0/0/1.0 host-inbound-traffic system-services ssh
set security address-book global address LAN-NET 10.0.0.0/24
set security policies from-zone trust to-zone untrust policy ALLOW-WEB match source-address LAN-NET destination-address any application [ junos-http junos-https junos-dns-udp ]
set security policies from-zone trust to-zone untrust policy ALLOW-WEB then permit
set security policies from-zone trust to-zone untrust policy ALLOW-WEB then log session-close
set security nat source rule-set T2U from zone trust
set security nat source rule-set T2U to zone untrust
set security nat source rule-set T2U rule R1 match source-address 10.0.0.0/24
set security nat source rule-set T2U rule R1 then source-nat interface
commit check
commit confirmed 5
```
Now test from a **new** SSH session and check traffic (`show security flow session`,
`show security policies hit-count`). Only then confirm, within the 5 minutes:
```
commit
```
If you don't confirm, Junos restores the previous configuration by itself.

Routing: OSPF inside, EBGP to the ISP, advertising a prefix you own (`198.51.100.0/24`). The
`discard` static route anchors the prefix so there is something to advertise; the import policy
accepts only a default route from the ISP. For a full table, accept it in the import policy and raise
`accepted-prefix-limit maximum` above the current full-table size (check it at the time; it keeps
growing), keeping `teardown`. The base config's static default (preference 5) beats the BGP default
(preference 170), so the BGP default is only a backup; to make it the primary path, delete the static
default once the BGP session is up, as its own `commit confirmed` step.
On an SRX the zones must also let BGP and OSPF reach the device itself (`host-inbound-traffic
protocols`); MX/EX have no zones, so skip the two `security zones` lines there. Paste in configuration mode
(after `configure`):
```
set interfaces ge-0/0/2 unit 0 family inet address 10.0.1.1/30
set security zones security-zone trust interfaces ge-0/0/2.0 host-inbound-traffic protocols ospf
set security zones security-zone untrust interfaces ge-0/0/0.0 host-inbound-traffic protocols bgp
set protocols ospf area 0.0.0.0 interface ge-0/0/1.0 passive
set protocols ospf area 0.0.0.0 interface ge-0/0/2.0
set routing-options autonomous-system 65001
set routing-options static route 198.51.100.0/24 discard
set policy-options prefix-list OWN-PREFIXES 198.51.100.0/24
set policy-options policy-statement EXPORT-BGP term OWN from protocol static
set policy-options policy-statement EXPORT-BGP term OWN from prefix-list OWN-PREFIXES
set policy-options policy-statement EXPORT-BGP term OWN then accept
set policy-options policy-statement EXPORT-BGP term REJECT then reject
set policy-options policy-statement IMPORT-BGP term DEFAULT from route-filter 0.0.0.0/0 exact
set policy-options policy-statement IMPORT-BGP term DEFAULT then accept
set policy-options policy-statement IMPORT-BGP term REJECT then reject
set protocols bgp group ISP type external
set protocols bgp group ISP peer-as 65000
set protocols bgp group ISP neighbor 203.0.113.1
set protocols bgp group ISP import IMPORT-BGP
set protocols bgp group ISP export EXPORT-BGP
set protocols bgp group ISP family inet unicast accepted-prefix-limit maximum 10 teardown
commit check
commit confirmed 5
```
Check `show bgp summary`, `show route receive-protocol bgp 203.0.113.1` and
`show route advertising-protocol bgp 203.0.113.1` (only `198.51.100.0/24` should be listed), then
confirm with `commit`.

EX/QFX (ELS) switching: `set vlans USERS vlan-id 10`, `set interfaces ge-0/0/2 unit 0 family ethernet-switching interface-mode access vlan members USERS`,
trunk `interface-mode trunk vlan members [ USERS VOICE ]`, L3 `set interfaces irb unit 10 family inet address 10.0.10.1/24` + `set vlans USERS l3-interface irb.10`.
**Never** add `no-readvertise` to the `discard` anchor route — it makes it ineligible for export.
Always pair EBGP with explicit import and export policies, plus `family inet unicast accepted-prefix-limit maximum <n> teardown`
(Junos EBGP is not RFC 8212-compliant by default: without policies, EBGP routes are accepted and advertised).
`host-inbound-traffic` set on an interface overrides the zone's setting for that category (`system-services` or `protocols`),
so check where SSH is allowed before adding anything at interface level, or you can drop your own remote session.
`rollback 1` after a confirmed commit restores the *previous* commit (often the new config itself) — check `show system commit` and pick the right number.
Route-based VPN: `security ike proposal/policy/gateway`, `security ipsec proposal/policy/vpn ... bind-interface st0.0`, put `st0.0` in a zone, route to `st0.0`.

Show: `show interfaces terse`, `show route`, `show ospf neighbor`, `show bgp summary`,
`show route advertising-protocol bgp 203.0.113.1`, `show security flow session source-prefix 10.0.0.5`,
`show security policies hit-count`, `show security match-policies from-zone trust to-zone untrust source-ip 10.0.0.5 destination-ip 8.8.8.8 protocol tcp source-port 1024 destination-port 443`,
`show security ike security-associations`, `show security ipsec security-associations`, `monitor traffic interface ge-0/0/1`,
`show | compare`, `show configuration | display set`, `rollback 1` then `commit`.
