---
tags: [skill-creator]
max_turns: 20
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

عندي Juniper SRX300 على Junos 22.4، وعايز أعمل BGP مع مزود الخدمة. الـ AS بتاعي 65010 والـ AS بتاع المزود 64500. الـ peer هو 203.0.113.1 وأنا 203.0.113.2/30 على ge-0/0/0 (zone untrust). عايز أعلن 198.51.100.0/24 بس، ومستقبلش من المزود غير الـ default route. اعملي الكونفيج كامل وأنا شغال عليه remote.
