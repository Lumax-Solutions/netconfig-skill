# Aruba / HPE — AOS-CX & ArubaOS-Switch

Part of the `network-config` skill. Read `../SKILL.md` first for the workflow and safety rules.

## Aruba / HPE

**AOS-CX** (CX 6xxx/8xxx):
```
configure terminal
vlan 10
    name USERS
interface 1/1/1
    no shutdown
    no routing
    vlan access 10
interface 1/1/48
    no shutdown
    no routing
    vlan trunk native 1
    vlan trunk allowed 10,20
interface lag 1
    no shutdown
    no routing
    vlan trunk allowed 10,20
    lacp mode active
interface vlan 10
    ip address 10.0.10.1/24
    ip helper-address 10.0.0.53
    ip ospf 1 area 0.0.0.0
router ospf 1
    router-id 1.1.1.1
    area 0.0.0.0
ip route 0.0.0.0/0 10.0.0.254
write memory
```
Ports are routed by default on many CX models (hence `no routing` for L2 ports). Safety: `checkpoint auto 10` (minutes) → `checkpoint auto confirm`; `copy running-config checkpoint PRE` / `checkpoint rollback PRE`. VSX for dual-chassis.
Show: `show interface brief`, `show vlan`, `show lacp interfaces`, `show ip route`, `show ip ospf neighbors`, `show lldp neighbor-info`.

**ArubaOS-Switch / ProCurve (legacy):** VLAN-centric: `vlan 10` → `name USERS` → `untagged 1-10` → `tagged 48` → `ip address 10.0.10.1 255.255.255.0`.
