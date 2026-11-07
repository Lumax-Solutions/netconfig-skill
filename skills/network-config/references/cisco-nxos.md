# Cisco NX-OS — Nexus

Part of the `network-config` skill. Read `../SKILL.md` first for the workflow and safety rules.

## Cisco NX-OS (Nexus)

Features must be enabled; masks are prefix-length; routing protocols attach on the interface.
```
feature ospf
feature bgp
feature interface-vlan
feature lacp
feature vpc
vlan 10
  name USERS
interface Vlan10
  no shutdown
  ip address 10.0.10.1/24
  ip router ospf 1 area 0.0.0.0
router ospf 1
  router-id 1.1.1.1
router bgp 65001
  router-id 1.1.1.1
  neighbor 203.0.113.1
    remote-as 65000
    address-family ipv4 unicast
interface Ethernet1/1
  switchport
  switchport mode trunk
  switchport trunk allowed vlan 10,20
  channel-group 10 mode active
vpc domain 1
  peer-keepalive destination 10.255.0.2 source 10.255.0.1 vrf management
interface port-channel1
  vpc peer-link
interface port-channel10
  vpc 10
```
Save `copy run start`. Safety: `checkpoint PRE-CHANGE` → `rollback running-config checkpoint PRE-CHANGE`.
Show: `show vpc`, `show port-channel summary`, `show ip route vrf all`, `show ip ospf neighbors`, `show bgp ipv4 unicast summary`, `ethanalyzer local interface inband`.
