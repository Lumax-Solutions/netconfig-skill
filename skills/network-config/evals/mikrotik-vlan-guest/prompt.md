---
tags: [skill-creator]
max_turns: 20
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

I have a MikroTik hAP ax3 on RouterOS 7.16. ether1 is WAN (DHCP from ISP). I want VLAN 10 "staff" (10.10.10.0/24) untagged on ether2 and ether3, VLAN 20 "guest" (10.20.20.0/24) untagged on ether4, and ether5 as a trunk to my access point carrying both VLANs tagged. DHCP for both VLANs, internet for both, guests must not reach staff or the router's admin (winbox/ssh/web). I'm configuring it through winbox connected on ether5 right now. Give me the full config.
