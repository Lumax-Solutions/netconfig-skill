### CASE A — Existing FortiGate conflict

**Do not create the new VIP or modify OLD-HTTPS yet.** The requested WAN IP, protocol, and port already belong to OLD-HTTPS. Replacing its mapping would redirect the old server’s traffic without authorization. WEB-02 also represents the old server; leave it unchanged.

There is a separate policy-order problem: policy 12’s blanket deny precedes policy 30, so matching inbound traffic is denied before reaching Old-Web.

The change plan is:

1. Obtain either a different available public IP, authorization to use a different external port, or explicit authorization to replace the old publication. Two ordinary VIP mappings cannot independently serve different servers on the identical public TCP endpoint.
2. Confirm whether the existing Old-Web service should become reachable; moving its policy above the deny would change its effective access.
3. Back up the configuration and record the existing VIP and policy settings. Automatic save means changes persist immediately.
4. Once the endpoint is approved, create a **separate VIP** mapping to `10.0.0.12:443`. Create any new server address object under a distinct name.
5. Create a narrowly scoped WAN-to-port2 accept policy referencing that VIP, with HTTPS service and logging. Place it above policy 12. With central NAT disabled, use the VIP in the firewall policy; ordinary inbound publication generally does not need policy source NAT.
6. Verify the new server’s return path goes through the FortiGate, then test externally and inspect policy logs.
7. For rollback, remove the new policy first, then the new VIP and any newly created unused objects.

Exact mutation commands depend on the approved public endpoint. Do not reuse `203.0.113.11:443` without resolving ownership.

### CASE B — Remote Cisco management restriction

Use a timed reload to restore the unchanged startup configuration if access is lost. **If the timer expires, the site will suffer a reload outage.** Keep the first SSH session open throughout.

First inspect the VTY settings and ensure the proposed ACL name is unused:

```text
show running-config | section line vty
show ip access-lists VTY_SSH_ONLY
show users
```

If `VTY_SSH_ONLY` already exists, stop and select an unused ACL name consistently below. Preserve all existing authentication commands.

Schedule recovery **before** making changes:

```text
reload in 10
```

Accept the confirmation prompt. If unexpectedly asked to save modified configuration, stop and investigate; the stated starting condition is that running and startup match.

Apply the restriction:

```text
configure terminal
ip access-list standard VTY_SSH_ONLY
 permit host 198.51.100.10
 exit
line vty 0 15
 access-class VTY_SSH_ONLY in
 transport input ssh
end
```

The ACL implicitly denies every other IPv4 source. No authentication commands are changed.

Verify configuration and timer:

```text
show ip access-lists VTY_SSH_ONLY
show running-config | section line vty
show reload
```

From `198.51.100.10`, **open a fresh second SSH connection** to `203.0.113.2` and authenticate normally. An existing session remaining connected is insufficient proof. In that new session, run:

```text
show users
show ip access-lists VTY_SSH_ONLY
```

Confirm both connections show the expected source. If another source is available for testing, verify that its new SSH connection is denied. This IPv4 ACL does not establish an IPv6 management restriction; investigate separately if IPv6 SSH is reachable.

After the fresh authorized session succeeds, cancel recovery and save:

```text
reload cancel
show reload
copy running-config startup-config
```

Accept the destination filename prompt. Verify persistence:

```text
show startup-config | section line vty
show startup-config | section ip access-list standard VTY_SSH_ONLY
```

**Recovery before saving:** If the new connection fails but the original still works, remove the restriction:

```text
configure terminal
line vty 0 15
 no access-class VTY_SSH_ONLY in
end
```

Retry a fresh SSH connection. Once access is confirmed, cancel the reload:

```text
reload cancel
show reload
```

Leave the unused ACL for later cleanup and restore the original `transport input` setting if it differed. Do not save a failed change.

If all SSH access is lost, allow the scheduled reload to restore the original startup configuration. Do not have anyone save the restricted running configuration.

### CASE C — Unknown production version

There is insufficient information for safe IP-change commands. Changing the address remotely could immediately remove your only management path.

Paste only these read-only discovery commands now:

```text
/system resource print
/system package print
/interface print
/ip address print detail
/ip route print detail
/user active print detail
/ip service print detail
```

Provide the output, the desired new IP/prefix and gateway, and the destination address you currently connect to. Redact sensitive identifiers consistently while preserving subnet relationships.

The next step is to identify your session’s interface and return route, then prepare a version-appropriate change using RouterOS Safe Mode, a temporary additional address where supported, and a verified second connection before removing the old address.