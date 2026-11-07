# Cisco IOS / IOS-XE — routers & Catalyst switches

Part of the `network-config` skill. Read `../SKILL.md` first for the workflow and safety rules.

## Cisco IOS / IOS-XE (ISR, ASR, Catalyst, CSR/C8000v)

```
! Basics & hardening
hostname R1
ip domain name example.local
crypto key generate rsa modulus 2048
ip ssh version 2
username admin privilege 15 secret <PASSWORD>
enable secret <PASSWORD>
service password-encryption
no ip http server
no ip http secure-server
ip access-list standard MGMT
 permit 10.0.99.0 0.0.0.255
line vty 0 15
 transport input ssh
 login local
 access-class MGMT in
 exec-timeout 10 0

! Interfaces
interface GigabitEthernet0/0
 description WAN
 ip address 203.0.113.2 255.255.255.252
 ip nat outside
 no shutdown
interface GigabitEthernet0/1
 description LAN
 ip address 10.0.0.1 255.255.255.0
 ip nat inside
 no shutdown

! Routing
ip route 0.0.0.0 0.0.0.0 203.0.113.1
router ospf 1
 router-id 1.1.1.1
 passive-interface default
 no passive-interface GigabitEthernet0/2
 network 10.0.0.0 0.0.0.255 area 0
router bgp 65001
 bgp router-id 1.1.1.1
 bgp log-neighbor-changes
 neighbor 203.0.113.1 remote-as 65000
 address-family ipv4
  network 198.51.100.0 mask 255.255.255.0
  neighbor 203.0.113.1 activate
  neighbor 203.0.113.1 prefix-list OUT out
 exit-address-family
ip prefix-list OUT seq 5 permit 198.51.100.0/24

! PAT + port forward
ip access-list standard NAT-LAN
 permit 10.0.0.0 0.0.0.255
ip nat inside source list NAT-LAN interface GigabitEthernet0/0 overload
ip nat inside source static tcp 10.0.0.10 443 interface GigabitEthernet0/0 443

! Extended ACL
ip access-list extended LAN-IN
 permit tcp 10.0.0.0 0.0.0.255 any eq 443
 permit udp 10.0.0.0 0.0.0.255 host 10.0.0.53 eq 53
 deny   ip any any log
interface GigabitEthernet0/1
 ip access-group LAN-IN in

! DHCP
ip dhcp excluded-address 10.0.0.1 10.0.0.20
ip dhcp pool LAN
 network 10.0.0.0 255.255.255.0
 default-router 10.0.0.1
 dns-server 10.0.0.53
```

**Switching (Catalyst):**
```
vlan 10
 name USERS
interface GigabitEthernet1/0/1
 switchport mode access
 switchport access vlan 10
 spanning-tree portfast
 spanning-tree bpduguard enable
interface GigabitEthernet1/0/48
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk allowed vlan 10,20
 switchport nonegotiate
interface Port-channel1
 switchport mode trunk
interface range GigabitEthernet1/0/47 - 48
 channel-group 1 mode active
ip routing
interface Vlan10
 ip address 10.0.10.1 255.255.255.0
 ip helper-address 10.0.0.53
spanning-tree mode rapid-pvst
```
(`switchport trunk encapsulation dot1q` only on platforms that also support ISL; `mode active` = LACP.)

**Route-based IPsec (IKEv2 + VTI):**
```
crypto ikev2 proposal P1
 encryption aes-cbc-256
 integrity sha256
 group 14
crypto ikev2 policy POL1
 proposal P1
crypto ikev2 keyring KR
 peer HQ
  address 198.51.100.1
  pre-shared-key <PSK>
crypto ikev2 profile PROF
 match identity remote address 198.51.100.1 255.255.255.255
 authentication remote pre-share
 authentication local pre-share
 keyring local KR
crypto ipsec transform-set TS esp-aes 256 esp-sha256-hmac
 mode tunnel
crypto ipsec profile IPSEC
 set transform-set TS
 set ikev2-profile PROF
interface Tunnel0
 ip address 169.254.10.1 255.255.255.252
 tunnel source GigabitEthernet0/0
 tunnel mode ipsec ipv4
 tunnel destination 198.51.100.1
 tunnel protection ipsec profile IPSEC
ip route 10.1.0.0 255.255.0.0 Tunnel0
ip route 10.1.0.0 255.255.0.0 Null0 254
```
The floating Null0 route stops remote-LAN traffic leaking out the WAN (in clear text,
via the default route/PAT) when the tunnel is down — the IOS equivalent of the FortiGate
blackhole route. Add it on **both** ends of any route-based VPN. Licensing (ISR 4000/C8000):
the SEC/securityk9 licence enables IPsec/ZBFW; without HSEC (`license feature hseck9`, export-controlled)
crypto is capped at 1,000 tunnels / 250 Mbps — check with `show license summary`.
A Cisco SVTI always uses "any any" (0.0.0.0/0) traffic selectors, so the peer's phase 2
must use 0.0.0.0/0 too (on FortiGate: src/dst-subnet 0.0.0.0 0.0.0.0) or the tunnel won't come up.
On a router that already has IKEv2 tunnels, a new `crypto ikev2 policy` without `match` matches all
peers in the global FVRF, so it can change what existing peers negotiate (how it interacts with the
smart-default policy isn't spelled out in Cisco's docs — test it). Check `show crypto ikev2 policy`
first; scope the new policy with `match address local <wan-ip>` or reuse the existing one.
Don't use `?` in a pre-shared key typed or pasted at the CLI (it triggers help and corrupts the key).
Enabling the security / HSEC licence may need a reload — plan it as a separate maintenance step.
`copy running-config bootflash:<file>` asks to confirm the destination name — press Enter.
Debug one peer only: `debug crypto condition peer ipv4 <peer-ip>` then `debug crypto ikev2`
(`undebug all` after). Common IKEv2 failures: `NO_PROPOSAL_CHOSEN` (crypto mismatch),
`AUTHENTICATION_FAILED` (PSK/identity), `TS_UNACCEPTABLE` (selectors — use 0/0 with a VTI).
Traffic routed into a VTI isn't PATed (the tunnel isn't `ip nat outside`), so the existing
PAT needs no exemption; for crypto-map VPNs, deny the VPN subnets in the NAT ACL instead.

**Inbound ACL on a NAT/PAT router's WAN:** the ACL sees return traffic *before* un-NAT and
is stateless, so `permit tcp any any established` + `deny ip any any` breaks return UDP
(DNS, QUIC, VoIP, VPN clients). Use a Zone-Based Firewall (`zone security`, `zone-pair`,
`inspect`) or CBAC for stateful filtering, or make the WAN ACL a deny-list of the router's
own management/services (22, 23, 80, 443, 161, 500/4500 if unused) ending in `permit ip any any`.

**HSRP:** `interface Vlan10` → `standby 10 ip 10.0.10.1` / `standby 10 priority 110` / `standby 10 preempt`.

**Safety & save:** `reload in 10` before risky remote changes, `reload cancel` after;
`archive` (with `path flash:archive` — **required** for the revert timer) + `configure replace flash:backup.cfg`;
IOS-XE: `configure terminal revert timer 10` then `configure confirm`. Save: `copy running-config startup-config`.

**Troubleshooting:** `show ip interface brief`, `show interfaces Gi0/0`, `show running-config | section bgp`,
`show ip route`, `show ip ospf neighbor`, `show ip bgp summary`, `show ip bgp neighbors X advertised-routes`,
`show access-lists` (hit counts), `show ip nat translations`, `show crypto ikev2 sa`, `show crypto ipsec sa`,
`show vlan brief`, `show interfaces trunk`, `show spanning-tree vlan 10`, `show etherchannel summary`,
`show cdp/lldp neighbors`, `show logging`, `ping 8.8.8.8 source Gi0/1`, `traceroute`.
IOS-XE packet capture (an inline `match ipv4 host X any` only catches packets *from* X, so use an ACL for both directions):
`ip access-list extended CAPACL` → `permit ip host 10.0.0.5 any` / `permit ip any host 10.0.0.5`;
`monitor capture CAP interface Gi0/0/1 both access-list CAPACL` → `monitor capture CAP start` / `stop` →
`show monitor capture CAP buffer brief` (capture name ≤ 8 chars on Cat9k).
Warn before any `debug` on production (use `terminal monitor`, narrow with ACL, `undebug all`).
