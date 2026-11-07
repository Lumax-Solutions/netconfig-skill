# MikroTik — RouterOS v7

Part of the `network-device-config` skill. Read `../SKILL.md` first for the workflow and safety rules.

## MikroTik RouterOS (v7; note v6 differences)

Default filter policy is **accept** – always build an explicit firewall. Use Safe Mode (Ctrl+X) when remote.
Avoid `/system reset-configuration` unless asked — build the VLAN design incrementally: keep the port you're managed through on its current untagged VLAN until you've moved to a new access port, then convert it.
Adding the port you're connected through to a bridge (or changing its PVID) drops that session — do it in its own step, or paste from an `.rsc` file with `/import`, so the rest of the script isn't cut off.
Rule order is top-down: put guest/isolation drops **above** generic accepts (e.g. `accept protocol=icmp`) or they never apply.
In bridge VLAN entries, include the bridge itself as `tagged` for any VLAN that has a `/interface vlan` L3 interface.
Guest isolation from router management also needs `/tool mac-server set allowed-interface-list=LAN`, `/tool mac-server mac-winbox set allowed-interface-list=LAN`, `/ip neighbor discovery-settings set discover-interface-list=LAN`, and IPv6 input rules if IPv6 is enabled.
```
/system identity set name=R1
/ip address add address=203.0.113.2/30 interface=ether1
/ip address add address=10.0.0.1/24 interface=bridge1
/ip route add dst-address=0.0.0.0/0 gateway=203.0.113.1
/ip dns set servers=1.1.1.1,8.8.8.8 allow-remote-requests=yes
/interface list add name=WAN
/interface list add name=LAN
/interface list member add list=WAN interface=ether1
/interface list member add list=LAN interface=bridge1
/ip firewall filter
add chain=input action=accept connection-state=established,related,untracked
add chain=input action=drop connection-state=invalid
add chain=input action=accept protocol=icmp
add chain=input action=accept in-interface-list=LAN
add chain=input action=drop comment="drop all else to router"
add chain=forward action=fasttrack-connection connection-state=established,related hw-offload=yes
add chain=forward action=accept connection-state=established,related,untracked
add chain=forward action=drop connection-state=invalid
add chain=forward action=drop in-interface-list=WAN connection-nat-state=!dstnat
/ip firewall nat
add chain=srcnat out-interface-list=WAN action=masquerade
add chain=dstnat in-interface-list=WAN protocol=tcp dst-port=443 action=dst-nat to-addresses=10.0.0.10 to-ports=443
/ip service disable telnet,ftp,www,api
/ip service set ssh address=10.0.0.0/24
/ip service set winbox address=10.0.0.0/24
```
VLANs (bridge VLAN filtering — enable `vlan-filtering=yes` **last** or you may lose access):
```
/interface bridge add name=bridge1
/interface bridge port add bridge=bridge1 interface=ether2 pvid=10
/interface bridge port add bridge=bridge1 interface=ether5
/interface bridge vlan add bridge=bridge1 vlan-ids=10 tagged=bridge1,ether5 untagged=ether2
/interface vlan add name=vlan10 interface=bridge1 vlan-id=10
/ip address add address=10.0.10.1/24 interface=vlan10
/interface bridge set bridge1 vlan-filtering=yes
```
OSPF v7: `/routing ospf instance add name=default router-id=1.1.1.1` → `/routing ospf area add name=backbone area-id=0.0.0.0 instance=default` → `/routing ospf interface-template add area=backbone networks=10.0.0.0/24`.
BGP v7 (7.1–7.19): `/routing bgp connection add name=ISP as=65001 remote.address=203.0.113.1 remote.as=65000 local.role=ebgp output.network=BGP-OUT` + `/ip firewall address-list add list=BGP-OUT address=198.51.100.0/24`.
RouterOS **7.20+** adds instances: `/routing bgp instance add name=default as=65001 router-id=1.1.1.1` then `/routing bgp connection add name=ISP instance=default remote.address=203.0.113.1 remote.as=65000 local.role=ebgp output.network=BGP-OUT` (`remote.as` is optional — learned from the peer). Check the version with `/system resource print`.
(v6 used `/routing ospf network` and `/routing bgp peer` — different syntax.)
IPsec: `/ip ipsec profile`, `/ip ipsec peer`, `/ip ipsec identity`, `/ip ipsec proposal`, `/ip ipsec policy`; WireGuard: `/interface wireguard` + `/interface wireguard peers`.
Show: `/interface print`, `/ip route print`, `/ip firewall filter print stats`, `/ip firewall connection print where src-address~"10.0.0.5"`,
`/tool ping`, `/tool traceroute`, `/tool sniffer quick ip-address=10.0.0.5`, `/routing ospf neighbor print`, `/routing bgp session print`, `/log print`.
Backup: `/export file=pre-change` (text) and `/system backup save name=pre-change` (binary, same model).
