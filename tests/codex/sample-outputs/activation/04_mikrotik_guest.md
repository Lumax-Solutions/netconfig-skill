Use a separate guest VLAN and subnet, with firewall rules allowing guests out through the Internet connection and blocking access to internal networks and router services. **Keep ether5 on its current staff/management network during the rollout.** Enabling bridge VLAN filtering is the main lockout risk.

This is a planning outline; no device connections, configuration changes, or file modifications were made.

| Item | Known or proposed | Check before implementation |
|---|---|---|
| Router | hAP ax3, RouterOS 7.20 | Existing bridge and Wi-Fi configuration |
| Management | You connect through ether5 | Preserve its current untagged access and router IP |
| Guest network | Example: VLAN 30, `192.168.30.0/24` | Confirm VLAN ID and subnet are unused, including VPN routes |
| Guest access | Separate guest SSID, optionally a wired port | Identify radios, access ports, and any AP trunks |
| Internet | Existing WAN connection | Check WAN interface list, NAT, and firewall order |

The proposed changes are:

- **Add:** guest VLAN interface on the bridge, gateway address, DHCP pool/server, and a guest SSID mapped to that VLAN.
- **Modify:** bridge VLAN membership, port admission settings, and firewall rules. Include the bridge itself as a tagged member of the guest VLAN so the router can provide its gateway and DHCP.
- **Preserve:** staff addressing and ether5’s current management path. Avoid combining this with a staff subnet migration.
- **Remove:** guests’ membership in the staff broadcast domain once the guest path has been verified.

For the hAP ax3’s RouterOS 7 Wi-Fi stack, review `/interface wifi` settings before choosing the SSID/VLAN configuration; legacy wireless examples may not apply.

The firewall needs two distinct policies:

| Traffic | Intended policy |
|---|---|
| Guest → router | Permit DHCP and, if the router supplies DNS, TCP/UDP 53; drop other guest input |
| Guest → Internet | Permit forwarding through the actual WAN, with working source NAT |
| Guest → staff, VPNs, other internal networks | Drop |
| Unsolicited traffic → guests | Drop unless explicitly required |

Place guest restrictions before broad rules that could accept the same traffic. **Do not add the guest interface to a trusted `LAN` list** if that list grants router access. Check FastTrack and established connections during testing: existing sessions can conceal policy mistakes. Internet-only forwarding also needs protection against reaching internal addresses through port forwards or hairpin NAT.

IP firewall rules do not block MAC Winbox or MAC Telnet. Restrict those services and neighbor discovery to trusted staff interfaces. Apply equivalent IPv6 isolation if guests receive IPv6; IPv4 rules alone are insufficient. Isolation between individual guests is a separate Wi-Fi/Layer-2 requirement if you want that too.

A safe rollout would be:

1. Review the current configuration and obtain a backup before implementation.
2. Enter RouterOS **Safe Mode** with Ctrl+X before management-affecting changes. RouterOS changes normally persist immediately; Safe Mode provides rollback if the controlling session fails.
3. Prepare guest addressing, DHCP, firewall policy, and VLAN membership.
4. Verify staff and ether5 membership—including the bridge’s own CPU-facing membership—then enable bridge VLAN filtering **last**, as its own step.
5. Move one test guest onto the new network. Open a **new management session through ether5** and complete these checks before leaving Safe Mode with Ctrl+X.

| Test | Expected |
|---|---|
| Guest DHCP and DNS | Correct guest subnet; resolution works |
| Guest Internet browsing | Works |
| Guest → staff host and VPN destination | Blocked |
| Guest → router management, using any router address | Blocked |
| Guest MAC Winbox/MAC Telnet | Blocked |
| New ether5 management session; staff Internet | Both still work |

To make the plan specific, the remaining information is your staff subnet/router IP, WAN interface, intended guest SSID or wired ports, and whether IPv6 is active. If you choose to collect configuration output yourself, these are read-only checks:

```routeros
/interface bridge print detail
/interface bridge port print detail
/interface bridge vlan print detail
/interface vlan print detail
/interface wifi print detail
/interface wifi datapath print detail
/interface list member print detail
/ip address print detail
/ip route print detail
/ip dhcp-server print detail
/ip firewall filter print detail
/ip firewall nat print detail
/ipv6 settings print
/ipv6 firewall filter print detail
```

Redact public addresses and identifying details before sharing, while preserving interface names, subnet relationships, and rule order.