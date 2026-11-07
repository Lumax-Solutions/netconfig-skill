First, please provide the OS versions so I can give you the correct read-only commands:

- **FortiGate:** `get system status`
- **Cisco ISR:** `show version`

Redact serial numbers, hostnames and secrets. Preserve subnet masks, ACL order and consistent IP mappings.

Alongside those, I need the following outputs or existing excerpts:

| Area | FortiGate | Cisco ISR |
|---|---|---|
| **VPN selectors and counters** | Relevant phase 1/phase 2 configuration; negotiated phase 2 selectors; inbound/outbound IPsec packet counters | Relevant crypto map or VTI/IPsec profile; crypto ACL; active IPsec SAs showing local/remote identities and encapsulation/decapsulation counters |
| **Routing** | Route lookup for the remote test host and local test host; relevant policy routes/SD-WAN rules; tunnel/LAN interface details | Route and CEF lookup for both test hosts; relevant interface configuration, VRF and policy-based routing |
| **NAT** | Matching firewall policies in order, including NAT settings; central SNAT rules if enabled; referenced address objects/IP pools; session entry for the test flow | NAT statements, referenced ACLs/route maps in order, inside/outside interface assignments, NAT statistics and translations for the test flow |
| **Filtering** | Relevant LAN-to-VPN and VPN-to-LAN policies, including referenced objects and available deny logs | Relevant interface ACLs and zone-based firewall policies, with hit counters |

Also include:

- One failing flow: **source host IP → destination host IP, protocol/port**, initiation direction and timestamp.
- Both protected subnet lists, peer IPs, and whether either side intentionally translates VPN traffic.
- Whether the ISR uses a **crypto map or VTI**, and the FortiGate VDOM/Cisco VRF involved.
- Whether “up” means **IKE only**, or an established IPsec/child SA for the failing subnet pair.

If an ordinary test is approved, capture IPsec counters on both ends **before and after the same small host-to-host test**. Leave counters intact. A router-originated ping can use a source outside the selectors and give misleading results.

These outputs let us check that selectors mirror each other, routing chooses the intended path, NAT preserves—or intentionally maps—the selected addresses, and encrypted packets reach and leave both ends. No configuration changes or debugging are needed for this first pass.