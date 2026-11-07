You need a **TCP/443 port-forward VIP plus an inbound firewall policy**. On an existing FortiGate, first check NAT mode, address ownership, overlapping VIPs, and policy order.

`203.0.113.11` is a documentation address; substitute your allocated public IP if this is a real deployment.

**Check the existing configuration**

These are read-only commands for you to run, in the relevant VDOM:

```text
get system status
get system ha status
show system interface wan1
show system zone
get router info routing-table all
show full-configuration system settings
show firewall vip
show firewall policy
show firewall address
show full-configuration system global
show vpn ssl settings
```

| Item | What to check |
|---|---|
| Public IP delivery | Your ISP must route the public IP to this firewall, or deliver it on wan1’s connected subnet. For on-link delivery, check VIP ARP handling and duplicate IP ownership. A secondary interface IP is generally unnecessary. |
| Server path | Identify the interface/zone leading to `10.0.0.12`. Confirm HTTPS listens, the host firewall permits it, and replies return through this FortiGate. |
| NAT mode | Check `central-nat`. The template below assumes **disabled**. With central NAT enabled, configure DNAT through the central-NAT workflow and use the mapped server address in the security policy. |
| Existing objects | Check for overlapping external IP/port mappings, including full-IP VIPs, and existing object names/policy IDs. |
| Policy order | Review actual list order. Check earlier denies with `show full-configuration firewall policy <ID>`; upgraded rules can retain different `match-vip` settings. Preserve intentional blocking rules. |
| Interface membership | If wan1 or the server interface belongs to a zone/SD-WAN zone, use the appropriate zone in the firewall policy. |
| Management | Check WAN HTTPS administration, `admin-sport`, SSL-VPN listeners, and your current management path for public-IP/443 conflicts. |
| HA | If clustered, make the eventual change on the primary and verify synchronization. |

Sanitized VIP, policy, interface, route, and NAT-mode output would allow an exact minimal diff.

**Conditional configuration example**

This is an advisory template for **policy NAT mode**. Replace `<SERVER_INTERFACE_OR_ZONE>`, `<WAN_POLICY_INTERFACE_OR_ZONE>`, and both policy IDs before use. Verify the names and new policy ID are unused. The placement ID must reflect your intended security policy order.

First, add the VIP:

```text
config firewall vip
    edit "VIP-WEB12-443"
        set extintf "wan1"
        set extip 203.0.113.11
        set mappedip "10.0.0.12"
        set portforward enable
        set protocol tcp
        set extport 443
        set mappedport 443
    next
end
```

Check that it maps only TCP/443 and does not overlap another VIP.

Then add the policy:

```text
config firewall policy
    edit <FREE_POLICY_ID>
        set name "Publish-WEB12-HTTPS"
        set srcintf "<WAN_POLICY_INTERFACE_OR_ZONE>"
        set dstintf "<SERVER_INTERFACE_OR_ZONE>"
        set srcaddr "all"
        set dstaddr "VIP-WEB12-443"
        set action accept
        set schedule "always"
        set service "HTTPS"
        set nat disable
        set logtraffic all
    next
    move <FREE_POLICY_ID> before <POLICY_ID_FOR_PLACEMENT>
end
```

Use approved source address objects instead of `all` if access is restricted. Disabling policy NAT preserves client IPs; the VIP provides destination NAT and stateful return translation. No separate reverse policy is needed for replies.

**Recovery and verification**

Back up the configuration through the GUI before any eventual change. FortiOS normally applies and saves changes automatically; check `cfg-save`. If management access must change, plan that separately with console access and an armed rollback—FortiGate revert mode can reboot the appliance.

| Test source | Destination/service | Expected result |
|---|---|---|
| External permitted client | Public IP, TCP/443 | Correct website and TLS certificate |
| External client | Public IP, unpublished ports | Remain blocked unless separately authorized |
| Excluded source, if restricted | Public IP, TCP/443 | Blocked |
| Admin workstation | Existing management SSH/HTTPS | New login succeeds |
| Existing users | Existing published service | Continues working |
| Internal client | Server, TCP/443 | Existing access continues working |

Test externally using the website hostname/SNI, and verify traffic logs show the new policy and translated server address. Internal access through the public hostname needs separate hairpin handling or split DNS.

For rollback, remove the newly added policy first, then its VIP, using the recorded ID/name. Restore any modified existing settings from the backup.