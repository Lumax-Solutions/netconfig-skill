---
tags: [skill-creator]
max_turns: 20
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

I need a site-to-site IPsec VPN between our HQ FortiGate 100F (FortiOS 7.4, WAN is port wan1 with public IP 203.0.113.10, LAN 192.168.10.0/24 on port "internal") and a branch Cisco ISR 4331 running IOS-XE 17.9 (WAN Gi0/0/0 = 198.51.100.20, LAN 192.168.20.0/24 on Gi0/0/1, it already does PAT for internet on Gi0/0/0). Give me the full config for both sides. I'll be doing the Cisco side remotely over SSH from HQ so I don't want to lose access.
