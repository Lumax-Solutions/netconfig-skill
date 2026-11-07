---
tags: [skill-creator]
max_turns: 20
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

Port forward on my FortiGate 60F (7.4.4) isn't working. I made a VIP NAS-8443 (extip 203.0.113.10 port 8443 -> 192.168.10.50 port 443) and a policy wan1 -> internal, dstaddr "NAS-LAN" (address object 192.168.10.50/32), service TCP-8443, action accept. Here's debug flow:

```
id=65308 trace_id=1 func=print_pkt_detail line=5895 msg="vd-root:0 received a packet(proto=6, 198.51.100.77:51544->203.0.113.10:8443) tun_id=0.0.0.0 from wan1. flag [S], seq 2834573911, ack 0, win 64240"
id=65308 trace_id=1 func=init_ip_session_common line=6076 msg="allocate a new session-0004a1b2, tun_id=0.0.0.0"
id=65308 trace_id=1 func=fw_pre_route_handler line=183 msg="VIP-192.168.10.50:443, outdev-wan1"
id=65308 trace_id=1 func=__ip_session_run_tuple line=3519 msg="DNAT 203.0.113.10:8443->192.168.10.50:443"
id=65308 trace_id=1 func=vf_ip_route_input_common line=2605 msg="find a route: flag=00000000 gw-192.168.10.50 via internal"
id=65308 trace_id=1 func=fw_forward_handler line=930 msg="Denied by forward policy check (policy 0)"
```
What's wrong and how do I fix it?
