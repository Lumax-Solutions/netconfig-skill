# Huawei — VRP & USG

Part of the `network-config` skill. Read `../SKILL.md` first for the workflow and safety rules.

## Huawei VRP (routers/switches) & USG firewalls

`undo` negates, `display` shows, `quit`/`return` exits. On VRP8 (NE/CE series) two-stage mode needs `commit`;
`commit trial <seconds>` (VRP8 only, not AR/VRP5) auto-reverts unless confirmed with `commit` (cancel: `abort trial`).
`nat server ... global current-interface` is entered in the WAN interface view; SSH also needs `ssh user <name> service-type stelnet`.
```
system-view
sysname R1
interface GigabitEthernet0/0/0
 ip address 203.0.113.2 255.255.255.252
 undo shutdown
ip route-static 0.0.0.0 0.0.0.0 203.0.113.1
ospf 1 router-id 1.1.1.1
 area 0.0.0.0
  network 10.0.0.0 0.0.0.255
bgp 65001
 router-id 1.1.1.1
 peer 203.0.113.1 as-number 65000
 ipv4-family unicast
  network 198.51.100.0 255.255.255.0
  peer 203.0.113.1 enable
vlan batch 10 20
interface GigabitEthernet0/0/1
 port link-type access
 port default vlan 10
interface GigabitEthernet0/0/24
 port link-type trunk
 port trunk allow-pass vlan 10 20
interface Vlanif10
 ip address 10.0.10.1 255.255.255.0
acl number 3000
 rule 5 permit tcp source 10.0.0.0 0.0.0.255 destination-port eq 443
 rule 100 deny ip
interface GigabitEthernet0/0/1
 traffic-filter inbound acl 3000
acl number 2000
 rule 5 permit source 10.0.0.0 0.0.0.255
interface GigabitEthernet0/0/0
 nat outbound 2000
 nat server protocol tcp global current-interface 443 inside 10.0.0.10 443
stelnet server enable
user-interface vty 0 4
 authentication-mode aaa
 protocol inbound ssh
return
save
```
USG firewall policy: `firewall zone trust` → `add interface ...`; `security-policy` → `rule name LAN-OUT` → `source-zone trust`, `destination-zone untrust`, `source-address 10.0.0.0 24`, `action permit`; NAT under `nat-policy`.
Show: `display ip interface brief`, `display ip routing-table`, `display ospf peer brief`, `display bgp peer`, `display vlan`, `display current-configuration | include ...`, `display acl 3000`, `display nat session all`, `display firewall session table`.
