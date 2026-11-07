# Palo Alto Networks — PAN-OS

Part of the `network-device-config` skill. Read `../SKILL.md` first for the workflow and safety rules.

## Palo Alto Networks PAN-OS (set format)

Changes go to candidate config; nothing is live until `commit`. Security rules use **pre-NAT IP
and post-NAT zone**.
```
configure
set network interface ethernet ethernet1/1 layer3 ip 203.0.113.2/30
set network interface ethernet ethernet1/2 layer3 ip 10.0.0.1/24
set network interface ethernet ethernet1/2 layer3 interface-management-profile ALLOW-PING
set zone untrust network layer3 ethernet1/1
set zone trust network layer3 ethernet1/2
set network virtual-router default interface [ ethernet1/1 ethernet1/2 ]
set network virtual-router default routing-table ip static-route DEFAULT destination 0.0.0.0/0 nexthop ip-address 203.0.113.1
set address LAN-NET ip-netmask 10.0.0.0/24
set address WEB-SRV ip-netmask 10.0.0.10/32
set rulebase security rules Trust-to-Internet from trust to untrust source LAN-NET destination any application [ web-browsing ssl dns ] service application-default action allow
set rulebase security rules Trust-to-Internet profile-setting group default
set rulebase nat rules SNAT-Internet from trust to untrust source LAN-NET destination any service any source-translation dynamic-ip-and-port interface-address interface ethernet1/1
# Inbound DNAT: NAT rule uses public IP, zone untrust->untrust
set rulebase nat rules DNAT-Web from untrust to untrust destination 203.0.113.2 service service-https destination-translation translated-address WEB-SRV
set rulebase security rules Inbound-Web from untrust to trust destination 203.0.113.2 application ssl service application-default action allow
validate full
commit
```
With the Advanced Routing Engine (PAN-OS 10.2+ when enabled — switching engines needs a commit **and a reboot**)
routing lives under `network logical-router <name> vrf default ...` instead of `virtual-router`. Panorama-managed firewalls: push via device-group/template, don't edit locally.
New boxes often ship with a `default-vwire` on ethernet1/1–1/2: check with `show network virtual-wire` in **configure** mode (op mode: `show virtual-wire all`) and delete it before making those interfaces layer3.
U-turn (internal users → public IP of an internal server): NAT rule from trust to untrust, destination public IP, DNAT to the server **and** SNAT to the trust interface IP; place it above the outbound SNAT rule; security rule is trust→trust to the public IP.

Troubleshoot (operational mode): `show interface all`, `show routing route`, `show session all filter source 10.0.0.5`,
`test security-policy-match from trust to untrust source 10.0.0.5 destination 8.8.8.8 protocol 6 destination-port 443`,
`test nat-policy-match ...`, `show vpn ike-sa`, `show vpn ipsec-sa`, `test vpn ike-sa gateway GW`,
`show counter global filter delta yes severity drop`, `debug dataplane packet-diag ...`, `show high-availability state`, `show system info`.
Rollback: `revert config` (discard candidate) or `load config version <n>` then commit.
