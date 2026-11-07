# Existing-device change workflow

Part of the `network-config` skill. Read `../SKILL.md` first for the workflow and safety rules.

Use this for any change to a device that is already running. The steps are in the core file:
**collect state → minimal diff → prepare recovery → apply in phases → acceptance test → save**.
This file holds the per-vendor commands for each step.

## Contents
1. Read-only state collection, per vendor
2. Building the diff and finding conflicts
3. Recovery: running vs saved config, per vendor
4. Phasing rules
5. Acceptance matrix
6. Worked example (FortiGate, add a published server)

## 1. Read-only state collection

Ask only for what the change touches. All commands below are read-only.

| Vendor | Version / HA | Interfaces & routes | Policies / ACLs | NAT | Objects (name clashes) | Management path |
|---|---|---|---|---|---|---|
| Cisco IOS/IOS-XE | `show version`, `show redundancy` (if HA) | `show ip interface brief`, `show ip route`, `show run interface <if>` | `show run \| section access-list`, `show ip access-lists` (hit counts), `show run \| include access-group` | `show run \| include ip nat`, `show ip nat translations` | `show run \| include object-group\|ip access-list` | `show run \| section line vty`, `show users`, `show ip ssh` |
| Cisco ASA | `show version`, `show failover` | `show interface ip brief`, `show route`, `show nameif` | `show run access-list`, `show access-list` (hit counts), `show run access-group` | `show run nat`, `show nat detail` | `show run object`, `show run object-group` | `show run ssh`, `show run http`, `show ssh sessions` |
| FortiGate | `get system status`, `get system ha status` | `show system interface <port>`, `get router info routing-table all` | `show firewall policy` (order matters, not ID) | `get system settings \| grep central-nat`, `show firewall vip`, `show firewall ippool` | `show firewall address`, `show firewall addrgrp`, `show firewall service custom` | `show system interface <port> \| grep allowaccess`, `show system admin` (trusthosts) |
| Palo Alto | `show system info`, `show high-availability state` | `show interface all`, `show routing route` | `show running security-policy` | `show running nat-policy` | `configure` → `show address`, `show address-group`, `show service` | `show interface management`, management profiles: `configure` → `show network profiles interface-management-profile` |
| Juniper Junos | `show version`, `show chassis cluster status` | `show interfaces terse`, `show route` | `show configuration security policies \| display set`, `show security policies hit-count` | `show configuration security nat \| display set` | `show configuration security address-book \| display set` | `show configuration system services`, host-inbound-traffic: `show configuration security zones \| display set` |
| MikroTik | `/system resource print`, `/system routerboard print` | `/interface print`, `/ip address print`, `/ip route print` | `/ip firewall filter print` (order = number), `/ipv6 firewall filter print` | `/ip firewall nat print` | `/ip firewall address-list print` | `/ip service print`, `/user active print`, `/tool mac-server print` |
| Huawei VRP | `display version` | `display ip interface brief`, `display ip routing-table` | `display acl all`, `display traffic-filter applied-record` (where supported) | `display nat server`, `display nat outbound` | `display current-configuration \| include acl` | `display current-configuration configuration user-interface` |
| Aruba AOS-CX | `show version`, `show vsx status` | `show interface brief`, `show ip route` | `show access-list`, `show access-list hitcounts ip <name>` (verify with `?`) | — | `show object-group` | `show ssh server`, `show running-config \| include ssh` |
| Linux | `uname -a`, `cat /etc/os-release` | `ip -br addr`, `ip route`, `ip -6 route` | `sudo nft list ruleset` or `sudo iptables -S` + `sudo ip6tables -S`, `sudo ufw status numbered` | `sudo nft list table ip nat` / `sudo iptables -t nat -S` | — | `echo $SSH_CLIENT`, `ss -tnp \| grep :22` |

Also ask: **which interface/IP is the user connected through right now**, and is there
out-of-band access (console, iLO/iDRAC, cloud serial console).

If the user pastes output, follow `sanitizing-configs.md` (warn about secrets, don't repeat them).

## 2. Building the diff and finding conflicts

Present the change as:

```text
ADD     firewall address "WEB-02"            10.0.0.12/32
ADD     firewall vip "VIP-WEB-02-443"        203.0.113.11:443 -> 10.0.0.12:443
ADD     firewall policy (new, placed before policy 12 "Deny-Inbound")
MODIFY  firewall addrgrp "WEB-SERVERS"       member: + "WEB-02"
REMOVE  —
```

Check, and report each as **OK** or **Conflict → resolution**:
- **Name or ID already used** — an object, rule name or rule ID that already exists. Reuse it if it
  is identical, otherwise pick a new name. On FortiGate use `edit 0` for new policies and `move`
  to place them; never `edit <existing id>` unless you mean to modify that policy.
- **Shadowing** — an earlier rule matching the same traffic (a broader deny above a new allow, or a
  broader allow making a new deny useless). State where the new rule goes and why.
- **Overlap** — subnets, VIP external IP/port, port-forwards or static NATs already in use;
  overlapping routes that change the path for other traffic.
- **Mode** — FortiGate central NAT vs policy NAT, PAN-OS legacy vs advanced routing, ASA pre/post
  8.3 NAT, Junos chassis cluster: the syntax depends on it.
- **References** — before removing or renaming anything, find what references it
  (FortiGate `diagnose sys cmdb refcnt show <path.name> <value>`, PAN-OS `show <object>` usage via
  GUI/Panorama, Cisco `show run | include <name>`).
- **HA** — on a cluster, change the primary only; check sync afterwards
  (`diagnose sys ha checksum cluster`, `show high-availability state`, `show chassis cluster status`, `show failover`).

## 3. Recovery: running vs saved config

The most common rollback mistake is restoring the wrong thing. "Running" = what the device is
doing now; "saved" = what it loads after a reboot.

| Vendor | When a change takes effect / persists | Auto-rollback for remote changes | Confirm | Cancel / roll back manually | Restore a saved backup |
|---|---|---|---|---|---|
| Cisco IOS-XE | Immediately / after `copy run start` | `archive` + `path flash:archive` set up, then `configure terminal revert timer <min>` (reverts running config) — or `reload in <min>` (reloads the **saved** config) | `configure confirm`; for `reload in`: `reload cancel` | `configure replace flash:archive-<n> force` | `configure replace flash:backup.cfg` |
| Cisco ASA | Immediately / after `write memory` | `reload in <min>` where supported (check `reload ?`); restores the **saved** config | `reload cancel` | Re-apply removed lines / `no` the added ones | `copy flash:backup.cfg running-config` merges — it does **not** replace; use `configure replace` on 9.x where available (check `configure ?`) |
| FortiGate | Immediately and saved on `end` (default `cfg-save automatic`) | `config system global` → `set cfg-save revert` + `set cfg-revert-timeout <sec>`: changes stay unsaved and the unit **reboots** to the last saved config if not saved in time | `execute cfg save` | `execute cfg reload` (discard unsaved changes, manual/revert mode) | `execute restore config ...` or GUI *Configuration revisions* — **reboots the unit** |
| Palo Alto | At `commit` / committed = saved | None on standalone firewalls (no confirm timer). PAN-OS 11.1+ Panorama-managed firewalls have Automated Commit Recovery: they revert if the commit breaks the Panorama connection | `commit` | Before commit: `revert config`. After: `load config version <n>` (or `load config from <file>`) then `commit` | `load config from <file>` + `commit` |
| Juniper Junos | At `commit` / committed = saved | `commit confirmed <min>` (reverts to the previous commit) | `commit` (or `commit check` first) | `rollback <n>` + `commit` — check `show system commit` for the right `<n>` | `load override <file>` + `commit` |
| MikroTik | Immediately and persistent | Safe Mode (Ctrl+X) — reverts if the session drops; for planned disconnects, a `/system scheduler` job that undoes the change | Ctrl+X again to leave Safe Mode | Remove/disable the added items | `/import file=<backup>.rsc` (text) or `/system backup load` (binary, same model, reboots) |
| Arista EOS | At session commit / after `copy run start` | `configure session <name>` → `commit timer hh:mm:ss` | `configure session <name> commit` (verify with `?`) | `abort` the session before commit, or let the timer expire | `configure replace flash:backup.cfg` |
| Aruba AOS-CX | Immediately / after `write memory` | `checkpoint auto <min>` | `checkpoint auto confirm` | `checkpoint rollback <name>` | `copy checkpoint <name> running-config` |
| Huawei VRP8 | At `commit` / after `save` | `commit trial [time]` (check the unit with `?`) | `commit` | `abort trial` | `startup saved-configuration <file>` + reboot |
| Huawei VRP5 | Immediately / after `save` | None built in (use a scheduled reboot only with care) | — | `undo` the added lines | `startup saved-configuration <file>` + reboot |
| Linux (nftables/iptables) | Immediately / after saving to the rules file | `(sleep 300 && nft -f /root/fw.bak) &` or `iptables-restore < /root/fw.bak` | `kill %1` (the timer job) | `nft -f /root/fw.bak` | Restore the rules file and reload the service |

Rules:
- Arm the rollback **before** the phase that could cut access, not after.
- Don't save/commit permanently until verification passes; on Cisco a save before `reload cancel`
  makes the reload come back with the new config.
- Where the only rollback is a reboot (FortiGate revert mode, `reload in`, VRP5), say that it
  causes an outage and needs the saved config to be the known-good one.
- Where there is no automatic rollback (PAN-OS, ASA without `reload in`), require out-of-band access
  or a second admin path before changing anything on the management path.

## 4. Phasing rules

- Phase 1: objects only (addresses, services, VIPs, address lists) — safe, no traffic effect.
- Phase 2: the policy/ACL/NAT change that carries traffic — verify with the matrix.
- Separate phase for anything on the **management path** (management interface, management ACL,
  routing to the admin network, VPN the admin uses, HA settings), each with an armed rollback and a
  test from a **new** session before continuing.
- Removals go last, after the replacement is verified (e.g. delete the old rule only after the new
  one shows hits).
- On HA pairs, check sync after each phase.

## 5. Acceptance matrix

For every firewall/ACL/NAT/routing change, give a table like:

| # | Source | Destination | Service | Expected | How to test |
|---|---|---|---|---|---|
| 1 | Internet (test host) | 203.0.113.11 | TCP/443 | Allow, reaches 10.0.0.12 | `curl -kI https://203.0.113.11` from outside; `diagnose debug flow` shows the new policy ID |
| 2 | Internet | 203.0.113.11 | TCP/22 | **Deny** | `nc -vz 203.0.113.11 22` times out; deny log entry |
| 3 | LAN 10.0.10.0/24 | 10.0.0.12 | TCP/443 | Unchanged (allow) | existing policy hit count increases |
| 4 | Admin PC | Device management IP | SSH/HTTPS | Still works | open a **new** session |

Include (about 6 rows): the traffic the change is for, at least one thing that must stay blocked,
one existing flow that must keep working, and management access. Prefer the platform's simulation tools before
real traffic: Cisco ASA `packet-tracer`, PAN-OS `test security-policy-match` / `test nat-policy-match`,
Junos `show security match-policies`, FortiGate `diagnose debug flow` with a test connection.

## 6. Worked example (FortiGate 7.4, publish a second web server)

User: "Publish 10.0.0.12 on 203.0.113.11 port 443, like our existing WEB-01."

1. **State:** ask for `get system status`, `get system settings | grep central-nat`,
   `show firewall vip`, `show firewall policy`, `show firewall address | grep -A3 WEB`.
2. **Conflicts found (example):** `WEB-02` already exists as 10.0.0.22 → use `WEB-02B`.
   Policy 12 "Deny-Inbound" (wan1→internal, all) sits above where the new policy would land → `move`
   the new policy before 12.
3. **Recovery:** `execute backup config ...`; this change doesn't touch management, so no revert
   timer needed — say so.
4. **Phases:** (1) address + VIP, (2) policy with an explicit free ID + `move` before 12, in one block.
5. **Matrix:** rows 1–4 above.
6. **Save:** automatic on `end` (default); check `show firewall policy <id>` and hit counts.
