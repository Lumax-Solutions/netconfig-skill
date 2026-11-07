## Case A — FortiGate conflict

**Do not apply a publishing change yet.** The requested public IP/protocol/port already belongs to the old server. A second VIP with that same tuple cannot safely publish a different server while preserving the existing mapping.

| Item | Found | Action |
|---|---|---|
| Platform / NAT | FortiOS 7.4.5, standalone, central NAT disabled | Use policy-based VIP configuration once the conflict is resolved |
| Management | SSH through port2; console available | Preserve management settings |
| Address name | `WEB-02` already means `10.0.0.22/32` | Preserve it; use a verified unused name if a new object is needed |
| VIP overlap | `OLD-HTTPS` owns `203.0.113.11:443/TCP` | Preserve it pending an authorized endpoint decision |
| Policy order | Deny 12 precedes allow 30 | Check `match-vip`; do not assume the old publication currently works |
| Persistence | Automatic configuration saving | Any applied change persists; reboot is not an undo |

Read-only checks:

```text
show firewall vip
show firewall policy
show full-configuration firewall policy 12 | grep match-vip
```

If `match-vip` is enabled, policy 12 can block the old VIP before policy 30. If disabled, the broad deny does not necessarily match that VIP traffic. **Do not move policy 30 as part of this request**: that could activate an existing publication and is a separate change.

**Change plan:**

- **Add:** Nothing yet.
- **Modify:** Nothing.
- **Remove:** Nothing.

The necessary next step is to allocate and confirm an unused public IP, approve a different external port, or explicitly authorize replacing the old publication. The exact requested tuple cannot serve both independent backends through ordinary destination NAT.

Once that decision exists, back up through the GUI, create a uniquely named VIP, and create a narrowly scoped WAN-to-port2 HTTPS policy referencing that VIP, placed before policy 12. Preserve client addresses by leaving inbound policy SNAT disabled. Verify the new destination, the old service, blocked unsolicited ports, and a fresh LAN SSH session. Undo would delete the new policy before deleting its referenced VIP.

## Case B — Cisco remote VTY restriction

**Use the supported reload timer as the recovery guard.** If access is lost, its expiry causes a site outage, then reloads the unchanged startup configuration.

| Item | Found / prerequisite | Action |
|---|---|---|
| Platform | IOS-XE 17.9 ISR | Apply a VTY access-class |
| Management | `198.51.100.10` → `203.0.113.2`, SSH; no console | Keep the current session and test a second session |
| Authentication | Working local authentication | Leave authentication and credentials unchanged |
| Existing VTY restriction | None on VTY 0–15 | Apply the same inbound ACL to all lines |
| ACL name | Must be unused | Check before creating `VTY_ONLY_198_51_100_10` |
| Recovery baseline | Startup equals running | Do not save until tests pass and the timer is canceled |

**Phase 0 — inspect and back up**

```text
show users
show running-config | section line vty
show ip ssh
show ip access-lists
copy running-config bootflash:pre-vty-restriction.cfg
```

Confirm the session source is `198.51.100.10`, inspect the existing transport settings, and verify the proposed ACL name is absent. Confirm the backup filename when prompted. If the name exists, select another unused name consistently throughout.

**Phase 1 — arm recovery before configuration**

```text
reload in 10
```

Confirm the reload prompt. If unexpectedly asked to save modified configuration, stop and investigate the baseline discrepancy; do not save.

```text
show reload
```

Proceed only after confirming the timer is armed and enough time remains.

**Phase 2 — create the ACL**

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

**Phase 3 — apply to the management lines**

```text
configure terminal
line vty 0 15
 access-class VTY_ONLY_198_51_100_10 in
 transport input ssh
exit
end
```

This retains the existing local authentication. Keep the original session open; immediately test a **new** session from `198.51.100.10`:

```text
ssh <existing-username>@203.0.113.2
```

Replace `<existing-username>` with your current username.

From the new session:

```text
show users
show running-config | section line vty
show ip access-lists VTY_ONLY_198_51_100_10
show reload
```

| Source | Destination | Service | Expected | Verification |
|---|---|---|---|---|
| `198.51.100.10` | `203.0.113.2` | New SSH session | Allowed | Log in with existing credentials |
| Any other controlled source | `203.0.113.2` | New SSH session | Blocked | Attempt SSH; inspect ACL counters |
| `198.51.100.10` | Router | Telnet | Blocked | Connection attempt rejected |
| Original admin session | Router | Existing SSH | Remains usable | Run a show command |
| Existing transit client | Existing destination | Existing service | Unchanged | Repeat a known working transaction |
| Admin | VTY 0–15 | Configuration | ACL on every line; authentication preserved | Inspect VTY configuration |

An established session alone does not verify the restriction. If no second source is available, record the negative SSH test as unperformed; inspect the explicit deny and line bindings.

**After verification — cancel recovery, then save**

```text
reload cancel
show reload
```

Confirm no reload remains scheduled before saving:

```text
copy running-config startup-config
```

**Manual recovery while a session remains usable**

Detach the ACL before deleting it:

```text
configure terminal
line vty 0 15
 no access-class VTY_ONLY_198_51_100_10 in
exit
no ip access-list standard VTY_ONLY_198_51_100_10
end
```

If Phase 3 removed previously permitted non-SSH transports, restore the exact original `transport input` line captured in Phase 0 to achieve a complete undo. Verify a fresh SSH session, then cancel the timer. If undoing **after saving**, save the verified restored configuration again.

If both sessions become inaccessible before saving, let the armed reload restore startup configuration. Do not cancel it until access has been recovered and verified.

## Case C — MikroTik unknown version and management path

**Only paste read-only discovery commands now.** A management-IP change needs the version, target address, interface, and return path before safe mutation commands can be specified.

Start with:

```text
/system resource print
/interface print
/ip address print
/ip route print
/ip service print
/user active print
/ip firewall filter print
/ip firewall nat print
```

Provide those outputs plus:

- Current destination IP and connection method, including any VPN or upstream NAT.
- Your client source IP as seen by the router.
- Desired new management IP/prefix and gateway, if applicable.
- Whether console or another independent management path is available.

The subsequent change should use Safe Mode, add and test the new address through a fresh session, and remove the old address only after the new path works. No IP-changing paste is justified with the current information.