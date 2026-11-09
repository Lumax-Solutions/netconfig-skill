# IPv6 and dual-stack

Part of the `network-config` skill. Read `../SKILL.md` first for the workflow and safety rules.

Examples use the documentation prefix `2001:db8::/32` (RFC 3849). Depth: Standard — verify
syntax on the device for your version.

## The dual-stack checklist (any vendor)

The classic failure is securing IPv4 and leaving IPv6 wide open, or breaking IPv6 by blocking ICMPv6.
For every change on a dual-stack device, check both families:

1. **Management access** — is the device reachable on an IPv6 address (often a link-local or
   SLAAC address you didn't configure)? Restrict SSH/HTTPS on IPv6 as well as IPv4.
2. **Firewall/ACL parity** — every IPv4 rule that matters needs an IPv6 equivalent. On Linux,
   iptables rules do **not** cover IPv6 (ip6tables is separate); nftables `inet` tables cover both.
3. **ICMPv6 is required** — Neighbor Discovery (types 133–137) and Packet Too Big (type 2) must be
   allowed or IPv6 breaks (no neighbour resolution, broken PMTU discovery). Don't copy an IPv4
   "deny all ICMP" rule to IPv6.
4. **No NAT by default** — IPv6 hosts are usually globally routable, so the firewall policy is the
   only protection; an IPv4 design that relied on NAT for "hiding" needs explicit IPv6 deny rules.
5. **Routing** — static/default routes and routing protocols are configured per family
   (OSPFv3, BGP `ipv6 unicast` address family, `rib inet6.0` on Junos).
6. **Verification** — test both families in the acceptance matrix (`ping`/`ping6`, `curl -6`,
   `traceroute6`), including at least one IPv6 flow that must stay blocked.

## Cisco IOS / IOS-XE

```
ipv6 unicast-routing
interface GigabitEthernet0/1
 ipv6 address 2001:db8:10::1/64
 ipv6 nd ra suppress all
interface GigabitEthernet0/0
 ipv6 address 2001:db8:ffff::2/64
ipv6 route ::/0 2001:db8:ffff::1
ipv6 access-list MGMT6
 permit ipv6 2001:db8:99::/64 any
line vty 0 15
 ipv6 access-class MGMT6 in
ipv6 access-list WAN6-IN
 permit icmp any any nd-na
 permit icmp any any nd-ns
 permit icmp any any packet-too-big
 permit icmp any any echo-reply
 deny ipv6 any any log
interface GigabitEthernet0/0
 ipv6 traffic-filter WAN6-IN in
```
Note: a Cisco IPv6 ACL has implicit `permit icmp any any nd-na` / `nd-ns` before its implicit deny,
but an explicit `deny ipv6 any any` placed at the end removes them — so permit ND explicitly as above.
`ipv6 nd ra suppress all` only if hosts on that segment should not autoconfigure from this router.
A stateless inbound IPv6 ACL like this also blocks return traffic for LAN-initiated connections —
on a router that is the IPv6 edge, use ZBFW or a reflexive/stateful design instead (same reasoning
as the IPv4 WAN ACL note in `cisco-ios.md`).
Show: `show ipv6 interface brief`, `show ipv6 route`, `show ipv6 access-list`, `show ipv6 neighbors`.

## FortiGate (FortiOS 7.x)

```
config system interface
    edit "port2"
        config ipv6
            set ip6-address 2001:db8:10::1/64
            set ip6-allowaccess ping
        end
    next
end
config router static6
    edit 0
        set gateway 2001:db8:ffff::1
        set device "port1"
    next
end
config firewall address6
    edit "LAN6"
        set ip6 2001:db8:10::/64
    next
end
```
Policies: since FortiOS 6.4.0 one `config firewall policy` entry carries both families
(`set srcaddr6` / `set dstaddr6` alongside `set srcaddr` / `set dstaddr`); 6.2 and older use a
separate `config firewall policy6`. Management: `set ip6-allowaccess` per interface is independent of IPv4 `allowaccess`,
and admin `trusthost` has IPv6 equivalents (`ip6-trusthost1`). Show: `diagnose ipv6 address list`,
`get router info6 routing-table`, `diagnose sniffer packet any 'ip6' 4 0 l`.

## Palo Alto PAN-OS

```
set network interface ethernet ethernet1/2 layer3 ipv6 enabled yes
set network interface ethernet ethernet1/2 layer3 ipv6 address 2001:db8:10::1/64
set network virtual-router default routing-table ipv6 static-route DEFAULT6 destination ::/0 nexthop ipv6-address 2001:db8:ffff::1
set address LAN6 ip-netmask 2001:db8:10::/64
```
Security rules are family-agnostic: the same rule matches IPv6 if its address objects (or `any`)
include IPv6, so a rule with `source any` already allows IPv6 — check existing `any` rules.
With the Advanced Routing Engine, routes are under `network logical-router`. Show:
`show routing route afi ipv6`, `show neighbor ndp interface all`.

## Juniper Junos (SRX)

```
set interfaces ge-0/0/1 unit 0 family inet6 address 2001:db8:10::1/64
set routing-options rib inet6.0 static route ::/0 next-hop 2001:db8:ffff::1
set security address-book global address LAN6 2001:db8:10::/64
```
On SRX, check that IPv6 is processed in flow mode: `show security flow status`. Enabling
flow-based IPv6 (`set security forwarding-options family inet6 mode flow-based`) needs a reboot on
many releases — plan it as a maintenance step. `host-inbound-traffic` applies to IPv6 too.
Security policies match IPv6 when their address-book entries are IPv6. Show: `show route table inet6.0`,
`show ipv6 neighbors`.

## MikroTik RouterOS v7

```
/ipv6 address add address=2001:db8:10::1/64 interface=bridge1 advertise=yes
/ipv6 route add dst-address=::/0 gateway=2001:db8:ffff::1
/ipv6 firewall filter
add chain=input action=accept connection-state=established,related,untracked
add chain=input action=drop connection-state=invalid
add chain=input action=accept protocol=icmpv6
add chain=input action=accept protocol=udp dst-port=546 src-address=fe80::/10 comment="DHCPv6-PD replies"
add chain=input action=accept in-interface-list=LAN
add chain=input action=drop
add chain=forward action=accept connection-state=established,related,untracked
add chain=forward action=drop connection-state=invalid
add chain=forward action=accept protocol=icmpv6
add chain=forward action=accept in-interface-list=LAN
add chain=forward action=drop
```
The IPv6 firewall is separate from `/ip firewall` and starts empty if the default config was
removed — with IPv6 enabled and no rules, the router and LAN are reachable over IPv6. Check
`/ipv6 settings print` and `/ipv6 firewall filter print`.

## Linux

- **nftables:** use `table inet filter` so one ruleset covers both families, and allow ICMPv6:
  `meta l4proto ipv6-icmp accept` (already in the example in `host-cloud.md`).
- **iptables:** every rule must be repeated with `ip6tables`, and saved separately
  (`rules.v6`; `netfilter-persistent save` writes both files on Debian/Ubuntu). Allow `-p ipv6-icmp`.
- **UFW:** `IPV6=yes` in `/etc/default/ufw` makes UFW rules apply to both families.
- Check exposure: `ss -tlnp` shows services listening on `[::]`.

## Other platforms

Cisco ASA (`ipv6 address`, `ipv6 route`, ACLs accept IPv6 objects), Huawei (`ipv6` in system view,
`ipv6 enable` + `ipv6 address` per interface, `acl ipv6`), Aruba AOS-CX (`ipv6 address`,
`ipv6 route`), Arista (`ipv6 unicast-routing`, `ipv6 address`): same checklist; verify syntax on
the device.
