# Cisco ASA & Firepower Threat Defense

Part of the `network-config` skill. Read `../SKILL.md` first for the workflow and safety rules.

## Cisco ASA

Post-8.3 rules: NAT is object/twice NAT, and **ACLs reference the real (untranslated) IP**.
```
interface GigabitEthernet0/0
 nameif outside
 security-level 0
 ip address 203.0.113.2 255.255.255.252
interface GigabitEthernet0/1
 nameif inside
 security-level 100
 ip address 10.0.0.1 255.255.255.0
route outside 0.0.0.0 0.0.0.0 203.0.113.1

object network INSIDE-NET
 subnet 10.0.0.0 255.255.255.0
 nat (inside,outside) dynamic interface
object network WEB-SRV
 host 10.0.0.10
 nat (inside,outside) static interface service tcp https https

access-list OUTSIDE-IN extended permit tcp any object WEB-SRV eq https
access-group OUTSIDE-IN in interface outside

! management
ssh 10.0.99.0 255.255.255.0 inside
ssh version 2
aaa authentication ssh console LOCAL
username admin password <PASSWORD> privilege 15
```

**Site-to-site IKEv2 (policy-based crypto map):**
```
object network LOCAL-NET
 subnet 10.0.0.0 255.255.255.0
object network REMOTE-NET
 subnet 10.1.0.0 255.255.255.0
crypto ikev2 policy 10
 encryption aes-256
 integrity sha256
 group 14
 prf sha256
 lifetime seconds 86400
crypto ikev2 enable outside
crypto ipsec ikev2 ipsec-proposal AES256
 protocol esp encryption aes-256
 protocol esp integrity sha-256
access-list VPN-HQ extended permit ip object LOCAL-NET object REMOTE-NET
tunnel-group 198.51.100.1 type ipsec-l2l
tunnel-group 198.51.100.1 ipsec-attributes
 ikev2 remote-authentication pre-shared-key <PSK>
 ikev2 local-authentication pre-shared-key <PSK>
crypto map OUTSIDE-MAP 10 match address VPN-HQ
crypto map OUTSIDE-MAP 10 set peer 198.51.100.1
crypto map OUTSIDE-MAP 10 set ikev2 ipsec-proposal AES256
crypto map OUTSIDE-MAP interface outside
nat (inside,outside) source static LOCAL-NET LOCAL-NET destination static REMOTE-NET REMOTE-NET no-proxy-arp route-lookup
```
(Route-based alternative: `interface Tunnel1` + `nameif`, `tunnel protection ipsec profile`.)

**Troubleshooting:** `packet-tracer input inside tcp 10.0.0.5 12345 8.8.8.8 443 detailed` (best first step),
`show nat detail`, `show xlate`, `show conn address 10.0.0.5`, `show access-list OUTSIDE-IN`,
`capture CAP interface inside match ip host 10.0.0.5 any` → `show capture CAP`,
`show crypto ikev2 sa`, `show crypto ipsec sa peer X`, `show vpn-sessiondb l2l`, `show failover`, `show asp drop`.
Save `write memory`.

## Cisco Firepower Threat Defense (FTD)

FTD is configured via **FMC / cdFMC / FDM** (GUI or REST API), not ASA CLI. Don't give ASA
`conf t` commands as if they apply. Explain the GUI path (Policies → Access Control, Devices →
NAT, Devices → VPN) or REST API calls. Unsupported features → FlexConfig.
CLI is for diagnostics: `show interface ip brief`, `packet-tracer ...`, `capture ...`,
`show conn`, `show nat`, `system support diagnostic-cli`, `system support trace`,
`configure manager add <FMC-IP> <regkey>`.
