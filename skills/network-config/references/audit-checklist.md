# Config review / audit checklist

Part of the `network-config` skill. Read `../SKILL.md` first for the workflow and safety rules.

## Config review / audit checklist

When asked to review a config, report findings as a table: **Severity (Critical/High/Medium/Low) | Finding | Evidence (line) | Fix (exact commands)**. Check:
1. **Management plane:** Telnet/HTTP enabled; management reachable from WAN; no source restriction (`access-class`, `trusthost`, `ip service address=`); default/weak/plain-text passwords (`password 0`, `enable password`); no AAA/TACACS/RADIUS; no MFA; no session timeout; SNMP v1/v2c with `public`/`private`.
2. **Policy:** any-any-any permits; rules shadowed by earlier broader rules; unused/zero-hit rules; services `ALL` from WAN; missing logging on deny/permit; inbound NAT exposing RDP/SMB/SSH/DB ports to the internet.
3. **VPN:** IKEv1 aggressive mode, DES/3DES/MD5/SHA-1, DH 1/2/5, weak PSKs, no PFS, overly broad proxy-IDs/selectors.
4. **Routing:** no route filtering on BGP (prefix-lists/max-prefix), no authentication on OSPF/BGP where required, missing blackhole routes for VPN subnets (FortiGate).
5. **L2:** unused ports enabled in VLAN 1, DTP on (`switchport nonegotiate`), no BPDU guard on access ports, native VLAN 1 on trunks, no port-security/DHCP snooping/DAI where needed.
6. **Operations:** NTP missing, no syslog server, no config backup/archive, outdated firmware (tell user to check vendor PSIRT advisories for that exact version).
Separate "definitely wrong" from "depends on intent" — ask about intent rather than assuming.
