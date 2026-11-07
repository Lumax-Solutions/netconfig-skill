---
tags: [skill-creator]
max_turns: 20
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

PA-440 on PAN-OS 11.1. ethernet1/1 is untrust with 203.0.113.26/29 (gateway 203.0.113.25), ethernet1/2 is trust 10.1.1.1/24. I need: (1) outbound internet for 10.1.1.0/24 using the interface IP, (2) publish internal web server 10.1.1.20 on public IP 203.0.113.27, HTTPS only, (3) internal users should also reach the web server using 203.0.113.27 (U-turn). Give me set commands.
