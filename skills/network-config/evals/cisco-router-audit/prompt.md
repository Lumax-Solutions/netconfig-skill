---
tags: [skill-creator]
max_turns: 20
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

Can you audit this branch router config and tell me what's wrong security-wise? It's a Cisco 1111.

```
hostname BR-RTR
enable password cisco123
username admin password 0 Admin@2020
no service password-encryption
ip http server
snmp-server community public RO
snmp-server community private RW
interface GigabitEthernet0/0/0
 ip address 203.0.113.50 255.255.255.252
 ip nat outside
interface GigabitEthernet0/1/0
 ip address 192.168.1.1 255.255.255.0
 ip nat inside
ip nat inside source list 1 interface GigabitEthernet0/0/0 overload
ip nat inside source static tcp 192.168.1.20 3389 interface GigabitEthernet0/0/0 3389
access-list 1 permit any
ip route 0.0.0.0 0.0.0.0 203.0.113.49
crypto isakmp policy 10
 encr 3des
 hash md5
 authentication pre-share
 group 2
crypto isakmp key cisco address 0.0.0.0
line vty 0 4
 password cisco
 login
 transport input telnet ssh
```
