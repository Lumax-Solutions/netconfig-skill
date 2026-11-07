### CASE A — FortiGate conflict

**Do not apply a publishing change yet.** The requested public TCP endpoint, `203.0.113.11:443`, already belongs to `OLD-HTTPS`. Redirecting it would replace the old server’s publication, which you have not authorized. `WEB-02` also represents the old server; do not modify it.

Policy 12’s broad deny precedes policy 30, so the supplied ordering also blocks the existing publication. Do not move policy 30 or alter policy 12 without approval to restore that access.

Necessary next step: select one of these options:

- Supply a different, available public IP for the new server.
- Approve a different external TCP port.
- Explicitly authorize migration of the existing endpoint, including the old server’s disposition.

Once selected, create a separate VIP and a narrowly scoped accept policy **before policy 12**, using the actual internal egress interface. Keep the old VIP, address object, and policy intact unless replacement is authorized. Confirm upstream delivery of the chosen public IP, server gateway and firewall, and external connectivity. Automatic saving means rollback must explicitly remove the new policy and VIP; disconnecting or rebooting will not undo them.

### CASE B — Cisco remote management restriction

Use an **unsaved change with a scheduled reload as recovery**. If access is lost, the reload restores the matching startup configuration but causes a site outage.

**1. Inspect from the existing session.**

```text
show users
show running-config | section line vty
show ip access-lists VTY_SSH_ONLY_198_51_100_10
show reload
```

Confirm the current SSH source is `198.51.100.10`, all VTY ranges are covered, and the proposed ACL name does not already exist. If it exists, choose an unused name and substitute it throughout. Resolve any existing scheduled reload before proceeding.

**2. Arm recovery before changing access.**

```text
reload in 10
```

Accept the confirmation. If unexpectedly prompted to save configuration, decline and investigate the startup/running discrepancy. Confirm the timer:

```text
show reload
```

**3. Apply the restriction without changing authentication.**

```text
configure terminal
ip access-list standard VTY_SSH_ONLY_198_51_100_10
 permit host 198.51.100.10
 deny any
exit
line vty 0 15
 access-class VTY_SSH_ONLY_198_51_100_10 in
 transport input ssh
end
```

Do **not** save yet. Existing local authentication remains unchanged.

**4. Open a fresh second SSH session from `198.51.100.10`.**

From that new session:

```text
show users
show running-config | section line vty
show ip access-lists VTY_SSH_ONLY_198_51_100_10
show reload
```

Verify successful fresh authentication, the inbound access-class on every VTY range, SSH-only transport, and unchanged authentication configuration. If another source is available for testing, confirm a fresh SSH attempt from it fails. Otherwise, denial is verified by configuration inspection only.

**5. After successful verification, cancel recovery and save.**

```text
reload cancel
show reload
copy running-config startup-config
```

Accept the destination filename prompt. Then verify:

```text
show startup-config | section line vty
show startup-config | section ip access-list standard VTY_SSH_ONLY_198_51_100_10
```

**Recovery:** If the second connection fails while the first remains usable, remove the restriction and cancel the reload:

```text
configure terminal
line vty 0 15
 no access-class VTY_SSH_ONLY_198_51_100_10 in
end
reload cancel
```

Restore the original `transport input` setting shown in step 1 if it differed, then remove the newly created ACL:

```text
configure terminal
no ip access-list standard VTY_SSH_ONLY_198_51_100_10
end
```

If all access is lost, **do not save**; let the scheduled reload restore startup configuration. Reconnect after the resulting outage.

### CASE C — Unknown MikroTik production version

**Do not paste management-IP change commands yet.** Without the current address, interface, session path, and intended new addressing, a remote change could disconnect your only access.

Paste these read-only discovery commands:

```text
/system resource print
/system package print
/interface print detail
/ip address print detail
/ip route print detail
/user active print detail
```

Provide the output with secrets redacted, plus the desired new IP/prefix, gateway if applicable, your client source IP, and whether console or another recovery path exists. Those details are needed to stage an additive address change, test a fresh connection, and only then remove the old address.