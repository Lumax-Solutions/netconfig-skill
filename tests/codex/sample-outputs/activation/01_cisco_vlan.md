Yes. The key command is **`switchport trunk allowed vlan add 20`**: `add` preserves the existing allowed VLANs. Without `add`, the command replaces the list.

Before finalizing the change, please share these read-only outputs, plus whether your management session traverses this uplink and whether console access is available:

```text
show running-config interface GigabitEthernet1/0/48
show interfaces GigabitEthernet1/0/48 switchport
show interfaces trunk
show etherchannel summary
show vlan id 20
show vtp status
```

These determine which commands are appropriate:

| Item | Required check |
|---|---|
| Uplink mode | Gi1/0/48 is already an operational Layer 2 trunk. |
| EtherChannel | If it belongs to a bundle, modify the **Port-channel**, not the physical member. |
| Allowed VLANs | If already `all` or already includes 20, no allowed-list change is needed. |
| Existing VLAN 20 | Confirm its purpose before reusing or renaming it. |
| VTP | A client cannot create VLANs locally; server changes may propagate. |

The **conditional draft**, assuming VLAN 20 is unused, local VLAN creation is appropriate, and Gi1/0/48 is a standalone trunk with a restricted list excluding 20, is:

1. Add VLAN 20:

```text
configure terminal
vlan 20
 name STAFF
end
```

Check with `show vlan id 20`.

2. Append it to the uplink:

```text
configure terminal
interface GigabitEthernet1/0/48
 switchport trunk allowed vlan add 20
end
```

Check with `show interfaces trunk`. The upstream device must also have VLAN 20 and permit it on its corresponding trunk. Preserve the existing native VLAN and trunk settings.

Before application, an operator should capture the baseline and back up the configuration:

```text
copy running-config flash:pre-vlan20.cfg
```

If the uplink carries management, prepare a verified IOS-XE timed rollback and console recovery before the uplink phase; the exact recovery plan depends on the current configuration.

Acceptance checks:

| Test | Expected |
|---|---|
| VLAN 20 status | Active locally |
| Trunk allowed list | Original VLANs retained; 20 included |
| STP forwarding | VLAN 20 forwards on the intended path |
| Staff connectivity | Works across the uplink using prepared endpoints |
| Existing services and fresh management session | Continue working |
| Existing prohibited traffic | Remains blocked under existing policy |

This change alone supplies Layer 2 transport; staff access ports, gateway, DHCP, and security policy must already exist or be planned separately.

After verification, save with:

```text
copy running-config startup-config
```

For the conditional draft above, undo the trunk addition with `switchport trunk allowed vlan remove 20` under the same interface. Delete VLAN 20 with `no vlan 20` **only if this change created it and nothing else now depends on it**. If it previously existed or was already permitted, preserve that baseline.