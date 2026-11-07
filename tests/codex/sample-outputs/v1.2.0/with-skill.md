### Case A — FortiGate: conflicting publication

**Do not change the configuration yet.** The requested public IP and port already belong to the old server; publishing the new server there would replace an existing service without authorization. A second VIP with the same external tuple does not resolve this.

| Item | Found | Action |
|---|---|---|
| Platform / mode | FortiOS 7.4.5, standalone, central NAT disabled | Use policy-based VIP configuration once the conflict is resolved |
| Management | SSH through port2; console available | Preserve management settings |
| Address object | `WEB-02` already means `10.0.0.22/32` | Preserve it; use a distinct name if a new object is needed |
| Public endpoint | `OLD-HTTPS` owns `203.0.113.11:443` | Preserve it |
| Policy order | Deny 12 precedes allow 30 | Inspect `match-vip`; order alone does not prove the existing VIP is blocked |
| Persistence | Automatic save | Applied changes persist; reboot is not an undo |

Necessary next step: obtain either an **unused, routed public IP**, an **approved alternative external port**, or **explicit authorization for a scheduled replacement** of the old publication.

Read-only checks for the eventual change plan:

```text
show firewall vip
show firewall address
show full-configuration firewall policy 12
show firewall policy 30
```

On FortiOS 7.4, a deny policy normally does not match VIP traffic unless `match-vip` is enabled. Do not enable it on policy 12 or move policy 30 as part of this request: either could change the old service’s behavior.

The eventual minimal diff should add a distinct VIP using the approved, nonconflicting endpoint and a dedicated HTTPS allow policy placed before policy 12. Reference the VIP as the policy destination, with inbound source NAT disabled. Preserve `WEB-02`, `OLD-HTTPS`, and policy 30.

Before applying that future diff, back up through the GUI or use this template after substituting a reachable TFTP server:

```text
execute backup config tftp pre-publish.conf <TFTP_SERVER_IP>
```

Acceptance must include the new endpoint reaching `10.0.0.12:443`, the old endpoint retaining its baseline behavior, unrelated ports staying blocked, and a new LAN SSH management session succeeding. Exact apply and undo commands depend on the approved endpoint; none are justified yet.

### Case B — Cisco: staged VTY restriction

This changes only VTY access and SSH transport. Existing local authentication remains intact.

| Item | Found / to check | Action |
|---|---|---|
| Platform | IOS-XE 17.9 ISR | Use a standard source ACL on VTY 0–15 |
| Management | SSH from `198.51.100.10` to `203.0.113.2`; no console | Keep the original session open and verify a second session |
| Existing state | Startup matches running; no VTY access-class | Preserve startup until verification finishes |
| ACL name | `VTY_ONLY_198_51_100_10` must be unused | Stop and choose another unused name if it exists |
| Recovery | Timed reload supported | Arm before applying; expiry causes a site outage |

**1. Inspect and back up**

```text
show users
show running-config | section line vty
show ip access-lists
show ip ssh
show reload
copy running-config bootflash:pre-vty-change.cfg
```

Press Enter to accept the backup filename. Confirm the observed session source, record the original `transport input` setting for each VTY range, and ensure no unrelated reload is pending.

**2. Arm recovery**

```text
reload in 10
```

Accept the confirmation prompt, then check:

```text
show reload
```

Proceed only when the timer is confirmed. **Do not save the running configuration.** If access is lost, the reload restores the unchanged startup configuration, with a site outage during reboot.

**3. Create the complete ACL before attaching it**

```text
configure terminal
ip access-list standard VTY_ONLY_198_51_100_10
 permit host 198.51.100.10
 deny any
exit
end
show ip access-lists VTY_ONLY_198_51_100_10
```

Check that the host permit precedes the deny.

**4. Apply to all VTY lines**

```text
configure terminal
line vty 0 15
 access-class VTY_ONLY_198_51_100_10 in
 transport input ssh
end
```

No `login`, AAA, username, password, interface ACL, routing, or NAT commands are changed.

**5. Verify before confirming**

From `198.51.100.10`, open a **new** SSH session to `203.0.113.2` using the existing credentials. In that session:

```text
show users
show running-config | section line vty
show ip access-lists VTY_ONLY_198_51_100_10
show ip ssh
show reload
```

| Source | Destination | Service | Expected | Test |
|---|---|---|---|---|
| `198.51.100.10` | `203.0.113.2` | New SSH | Allowed | Log in through a second session |
| Another reachable IPv4 host | `203.0.113.2` | New SSH | Denied | Attempt a new connection; inspect deny counter |
| `198.51.100.10` | Router | Telnet | Denied | Connection attempt |
| Original admin session | Router | SSH | Still usable | Run a show command |
| Existing credentials | Router | SSH authentication | Unchanged | Authenticate in the second session |
| Existing site clients | Existing destination | Known production service | Unchanged | Repeat an established baseline test |

A failed connection from another host is strongest evidence when paired with an ACL deny-counter increment. If that test host is unavailable, record that negative testing remains incomplete.

**6. Confirm, then save**

After successful verification, from the new session:

```text
reload cancel
show reload
```

Confirm that no reload remains scheduled, then:

```text
copy running-config startup-config
```

Do not reverse this order.

**Recovery / undo**

If a session still works but the new login fails, remove the attachment first:

```text
configure terminal
line vty 0 15
 no access-class VTY_ONLY_198_51_100_10 in
exit
no ip access-list standard VTY_ONLY_198_51_100_10
end
```

Restore any changed `transport input` settings exactly as recorded in phase 1. Verify a new login, then cancel the reload. If all sessions are lost, leave the timer armed and reconnect after the reboot.

After the final save, the same manual undo restores access, but must itself be saved after verification. The backup also supports full restoration with `configure replace bootflash:pre-vty-change.cfg force`; that replaces the entire running configuration, so prefer the targeted undo.

This ACL addresses IPv4 sources. If IPv6 management is enabled, its VTY restriction also needs inspection before claiming that SSH is restricted across both address families.

### Case C — MikroTik: collect version and management path first

Do not paste management-IP changes yet. The live version, target address, interface, and return path are unknown.

Paste only this read-only version command now:

```text
/system resource print
```

Provide its output together with:

- Current management destination IP and your client/source IP, including any VPN or jump host.
- Desired new IP/prefix and intended management interface or VLAN.
- Whether console or another independent management path is available.

Then collect the relevant interface, address, route, and management-filter state. The resulting change should add the new address while retaining the old one, use Safe Mode with a recovery plan appropriate to any expected disconnect, verify a new session through the new address, and remove the old address only afterward. RouterOS changes persist immediately; a reboot alone does not undo them.