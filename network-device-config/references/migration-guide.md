# Cross-vendor migration guide

Part of the `network-device-config` skill. Read `../SKILL.md` first for the workflow and safety rules.

## Cross-vendor migration (e.g. Cisco ASA → FortiGate, Cisco → Palo Alto)

Approach:
1. **Inventory** the source: interfaces/zones, routes, objects, groups, services, ACL/policies, NAT, VPNs, users/auth, HA. Count them so nothing is silently dropped.
2. **Map concepts** (concept map in SKILL.md). Key gotchas:
   - ASA security-levels allow high→low implicitly; the target (FortiGate/PAN/SRX) denies by default → create explicit outbound policies.
   - ASA ACLs use real IPs; FortiGate inbound policies use the **VIP object** as dstaddr; PAN-OS rules use **pre-NAT IP + post-NAT zone**; Junos policies use real IPs (destination NAT happens before policy).
   - Cisco IOS ACLs use **wildcard masks** (`0.0.0.255`) — convert to subnet masks/prefixes.
   - Interface ACLs (per interface, per direction) become zone/interface-pair policies; one ACL may split into several policies.
   - Service names differ (`eq www` → `HTTP`, `https` → `HTTPS`/`service-https`/`junos-https`); define custom services for the rest.
   - Object name rules: avoid spaces/special characters; FortiGate names are max 79 chars, quote names with spaces.
   - Policy-based (crypto map) VPN → route-based on the target is usually preferable; proxy-IDs/selectors must match the peer exactly.
   - Twice/identity NAT for VPN traffic (ASA) → on FortiGate simply leave NAT disabled on the VPN policy.
   - ASA object static NAT (`nat (dmz,outside) static 203.0.113.3`) → FortiGate static-NAT VIP (no portforward); outbound SNAT to the public IP happens automatically on NAT-enabled policies via extintf (see `fortigate.md`, VIP behaviour). ASA `static interface service ...` → port-forward VIP on the interface IP.
   - An interface with an ASA ACL applied loses its security-level implicit permits; interfaces with **no** ACL keep them — convert both cases explicitly (e.g. inside→outside and inside→dmz).
   - Always include pre-checks (central NAT off, interfaces free of default switch/zone membership), a backup command and a rollback/cutback plan (move cables back, clear ARP on the ISP router).
3. **Output** the converted config grouped in dependency order (interfaces → zones → objects → services → routes → NAT/VIPs → policies → VPN), plus a **mapping table** (source line → target object/policy) and a list of items that could not be converted automatically (e.g. inspection/`policy-map`, AAA, ASA-specific features) for manual review.
4. Recommend testing in a lab/maintenance window, and verifying hit counts after cutover.
   Mention vendor tools where relevant: FortiConverter (Fortinet), Cisco FMT (Firewall Migration Tool, ASA→FTD). Palo Alto Expedition is end-of-life (unsupported since January 2025) — migrations to PAN-OS go through Palo Alto Professional Services / partners, cleanup features are moving into Strata Cloud Manager.
