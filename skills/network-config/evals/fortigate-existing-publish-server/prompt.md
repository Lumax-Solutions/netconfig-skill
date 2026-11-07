---
tags: [skill-creator]
max_turns: 20
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

We have a FortiGate 60F on 7.4.4 in production, I manage it remotely over HTTPS on wan1. I need to publish a new web server 10.0.0.12 on our second public IP 203.0.113.11 port 443, and allow SSH to it only from our office 198.51.100.50. Here's the relevant part of the current config:

```
config system interface
    edit "wan1"
        set ip 203.0.113.10 255.255.255.248
        set allowaccess ping https
    next
end
config firewall address
    edit "WEB-01"
        set subnet 10.0.0.11 255.255.255.255
    next
    edit "WEB-02"
        set subnet 10.0.0.22 255.255.255.255
    next
end
config firewall vip
    edit "VIP-WEB-01"
        set extip 203.0.113.10
        set mappedip "10.0.0.11"
        set extintf "wan1"
        set portforward enable
        set extport 8443
        set mappedport 443
    next
    edit "VIP-OLD-CAMERA"
        set extip 203.0.113.11
        set mappedip "10.0.0.50"
        set extintf "wan1"
        set portforward enable
        set extport 443
        set mappedport 443
    next
end
config firewall policy
    edit 9
        set name "Block-Inbound-Bad"
        set srcintf "wan1"
        set dstintf "internal"
        set srcaddr "all"
        set dstaddr "all"
        set action deny
        set schedule "always"
        set service "ALL"
        set logtraffic all
    next
    edit 4
        set name "Inbound-WEB-01"
        set srcintf "wan1"
        set dstintf "internal"
        set srcaddr "all"
        set dstaddr "VIP-WEB-01"
        set action accept
        set schedule "always"
        set service "HTTPS"
    next
end
```
Give me what to paste.
