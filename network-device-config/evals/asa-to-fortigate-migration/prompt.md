---
tags: [skill-creator]
max_turns: 20
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

We're replacing an old Cisco ASA 5516 with a FortiGate 200F (FortiOS 7.2). Convert this ASA config to FortiGate CLI. Map ASA inside->port2, outside->port1, dmz->port3.

```
interface GigabitEthernet1/1
 nameif outside
 security-level 0
 ip address 203.0.113.2 255.255.255.248
interface GigabitEthernet1/2
 nameif inside
 security-level 100
 ip address 10.10.0.1 255.255.0.0
interface GigabitEthernet1/3
 nameif dmz
 security-level 50
 ip address 172.16.50.1 255.255.255.0
object network INSIDE-NET
 subnet 10.10.0.0 255.255.0.0
 nat (inside,outside) dynamic interface
object network DMZ-NET
 subnet 172.16.50.0 255.255.255.0
 nat (dmz,outside) dynamic interface
object network WEB01
 host 172.16.50.10
 nat (dmz,outside) static 203.0.113.3
object network MAIL01
 host 172.16.50.20
 nat (dmz,outside) static interface service tcp smtp smtp
object-group service WEB-PORTS tcp
 port-object eq www
 port-object eq https
access-list OUTSIDE-IN extended permit tcp any object WEB01 object-group WEB-PORTS
access-list OUTSIDE-IN extended permit tcp any object MAIL01 eq smtp
access-list DMZ-IN extended permit udp object DMZ-NET host 10.10.1.53 eq domain
access-list DMZ-IN extended deny ip object DMZ-NET 10.10.0.0 255.255.0.0
access-list DMZ-IN extended permit ip object DMZ-NET any
access-group OUTSIDE-IN in interface outside
access-group DMZ-IN in interface dmz
route outside 0.0.0.0 0.0.0.0 203.0.113.1
```
