# Fortinet FortiGate — FortiOS 7.x

Part of the `network-device-config` skill. Read `../SKILL.md` first for the workflow and safety rules.

## Fortinet FortiGate (FortiOS 7.x)

Syntax: `config <path>` → `edit <name|id>` → `set ...` → `next` → `end`. Changes apply and
save on `end`. `edit 0` creates the next free ID. Names with spaces need quotes.
With VDOMs enabled, prefix with `config vdom` → `edit <vdom>`.
```
config system interface
    edit "port1"
        set mode static
        set ip 203.0.113.2 255.255.255.252
        set allowaccess ping
        set role wan
    next
    edit "port2"
        set ip 10.0.0.1 255.255.255.0
        set allowaccess ping https ssh
        set role lan
    next
    edit "VLAN10"
        set vdom "root"
        set interface "port2"
        set vlanid 10
        set ip 10.0.10.1 255.255.255.0
        set allowaccess ping
    next
end

config router static
    edit 0
        set gateway 203.0.113.1
        set device "port1"
    next
end

config firewall address
    edit "LAN-NET"
        set subnet 10.0.0.0 255.255.255.0
    next
    edit "WEB-SRV"
        set subnet 10.0.0.10 255.255.255.255
    next
end
config firewall addrgrp
    edit "SERVERS"
        set member "WEB-SRV"
    next
end
config firewall service custom
    edit "TCP-8443"
        set tcp-portrange 8443
    next
end

config firewall policy
    edit 0
        set name "LAN-to-Internet"
        set srcintf "port2"
        set dstintf "port1"
        set srcaddr "LAN-NET"
        set dstaddr "all"
        set action accept
        set schedule "always"
        set service "ALL"
        set nat enable
        set utm-status enable
        set ssl-ssh-profile "certificate-inspection"
        set av-profile "default"
        set webfilter-profile "default"
        set logtraffic all
    next
end

config firewall vip
    edit "VIP-WEB-443"
        set extip 203.0.113.2
        set mappedip "10.0.0.10"
        set extintf "port1"
        set portforward enable
        set extport 443
        set mappedport 443
    next
end
config firewall policy
    edit 0
        set name "Inbound-Web"
        set srcintf "port1"
        set dstintf "port2"
        set srcaddr "all"
        set dstaddr "VIP-WEB-443"
        set action accept
        set schedule "always"
        set service "HTTPS"
        set logtraffic all
    next
end
```
The port-forward VIP above is used as dstaddr in the WAN→LAN policy.

**VIP behaviour (important for migrations):**
- A **static-NAT VIP** (no `portforward`) is bidirectional: inbound to `extip` is DNATed, and
  outbound traffic *from* `mappedip` that hits a NAT-enabled policy leaving via the VIP's
  `extintf` is automatically SNATed to `extip` (in policy-based NAT mode the VIP must be used in at
  least one policy; an IP pool on the outbound policy takes priority over the VIP). You do **not** need `set nat-source-vip enable`
  for that — it forces the SNAT on every policy (even NAT-disabled ones / other interfaces) and is
  rarely wanted.
- A **port-forward VIP** only DNATs; outbound from the server uses the policy's NAT (interface IP or IP pool).
- **Hairpin** (internal users reaching the server by its public IP): set the VIP `extintf "any"`
  (or create a second VIP for the internal interface) and add an internal→server-interface policy
  with the VIP as dstaddr. A port2→port1 policy with the VIP will *not* match. Caveat: an `any` VIP
  also SNATs the server's outbound traffic to extip on **every** interface — limit it with
  `set srcintf-filter "port1" "port2"` (CLI only) or prefer a specific extintf.
- Inbound policies reference the VIP (not the real IP) as dstaddr; don't also enable NAT on them
  unless you intend to hide the client IP.

Policy order matters: `config firewall policy` → `move <id> before <id>`.
SNAT pool: `config firewall ippool` + `set ippool enable` / `set poolname` in policy.
Central NAT mode (`config system settings` → `set central-nat enable`) moves NAT into
`config firewall central-snat-map` — check which mode the box uses before writing NAT.

**Routing:**
```
config router ospf
    set router-id 1.1.1.1
    config area
        edit 0.0.0.0
        next
    end
    config network
        edit 1
            set prefix 10.0.0.0 255.255.255.0
            set area 0.0.0.0
        next
    end
end
config router bgp
    set as 65001
    set router-id 1.1.1.1
    config neighbor
        edit "203.0.113.1"
            set remote-as 65000
        next
    end
    config network
        edit 1
            set prefix 198.51.100.0 255.255.255.0
        next
    end
end
```

**Route-based IPsec site-to-site:**
```
config vpn ipsec phase1-interface
    edit "TO-HQ"
        set interface "port1"
        set ike-version 2
        set peertype any
        set net-device disable
        set proposal aes256-sha256
        set dhgrp 14
        set remote-gw 198.51.100.1
        set psksecret <PSK>
    next
end
config vpn ipsec phase2-interface
    edit "TO-HQ-P2"
        set phase1name "TO-HQ"
        set proposal aes256-sha256
        set dhgrp 14
        set src-subnet 10.0.0.0 255.255.255.0
        set dst-subnet 10.1.0.0 255.255.255.0
    next
end
config router static
    edit 0
        set dst 10.1.0.0 255.255.255.0
        set device "TO-HQ"
    next
    edit 0
        set dst 10.1.0.0 255.255.255.0
        set blackhole enable
        set distance 254
    next
end
```
Then add two firewall policies: port2 → TO-HQ and TO-HQ → port2, both with NAT disabled.
Set `peertype any` explicitly (CLI default is `peer`). If the peer is a Cisco VTI, use
`src-subnet 0.0.0.0 0.0.0.0` / `dst-subnet 0.0.0.0 0.0.0.0` in phase 2 and rely on routes.

**SD-WAN (6.4.1+/7.x; 6.4.0 and older use `config system virtual-wan-link`):** `config system sdwan` → `set status enable`, `config zone`,
`config members` (interface + gateway), `config health-check` (server, members), `config service`
(rules). Policies then use the SD-WAN zone as dstintf. Interfaces in use by policies/routes must be
freed before adding as members.

**HA (FGCP):** `config system ha` → `set group-name`, `set mode a-p`, `set password <PASSWORD>`,
`set hbdev "port9" 50`, `set priority 200`, `set override disable`, `set monitor "port1" "port2"`.

**Hardening:** remove `http`/`telnet` from WAN `allowaccess`; `config system admin` → `set trusthost1`;
`config system global` → `set admin-sport 8443`, `set admintimeout 10`, `set admin-lockout-threshold 3`;
enable MFA (FortiToken); keep firmware current (check PSIRT advisories — SSL-VPN has been a frequent target,
and SSL-VPN tunnel mode was removed in FortiOS 7.6.3 — web mode remains as "Agentless VPN", disabled by default;
models with ≤2 GB RAM have no SSL-VPN at all; Fortinet's path is IPsec dial-up with FortiClient).

**Troubleshooting:**
```
get system status
get system interface physical
get router info routing-table all
get router info ospf neighbor
get router info bgp summary
show firewall policy | grep -f "LAN-NET"
diagnose sniffer packet any 'host 10.0.0.5 and port 443' 4 0 l
# policy/route decision trace (best first step for "traffic is blocked")
diagnose debug reset
diagnose debug flow filter addr 10.0.0.5
diagnose debug flow show function-name enable
diagnose debug console timestamp enable
diagnose debug enable
diagnose debug flow trace start 20
diagnose debug disable
# sessions
diagnose sys session filter src 10.0.0.5
diagnose sys session list
# VPN
get vpn ipsec tunnel summary
diagnose vpn ike gateway list name TO-HQ
diagnose vpn tunnel list name TO-HQ
diagnose vpn ike log filter rem-addr4 198.51.100.1
diagnose debug application ike -1
diagnose debug enable
execute ping-options source 10.0.0.1
execute ping 10.1.0.1
diagnose sys sdwan health-check
get system ha status
```
IKE debug filter syntax is version-specific: **7.4.1+** `diagnose vpn ike log filter rem-addr4 <ip>` (or `... log filter name <tunnel>`);
**7.4.0 and older** (6.x, 7.0, 7.2) `diagnose vpn ike log-filter dst-addr4 <ip>`. Match the stated version.
`execute ping-options source` takes an IP, not an interface name; the sniffer's 3rd arg is verbosity (1-6), 4th the count (0 = until Ctrl+C).
Backup: `execute backup config tftp <file> <server>` or GUI. Always `diagnose debug disable` afterwards.
Warn: `purge` deletes every entry in a table; `delete` on an object fails if referenced (check with
`diagnose sys cmdb refcnt show firewall.address.name LAN-NET` or GUI "Ref."). Field length limits: use `tree` in the CLI.
