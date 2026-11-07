A router decides where to send a packet by examining its **destination IP address** and looking it up in a **routing table**.

The process works like this:

1. **Read the destination address.** The router checks which IP address the packet is trying to reach.
2. **Find the most specific matching route.** Each routing-table entry covers a network. If several entries match, the router chooses the one with the longest matching network prefix—called **longest-prefix matching**.
3. **Identify the next step.** The chosen route specifies an outgoing interface and usually a **next-hop router**. If the destination is on a directly connected network, the router can send directly to the destination.
4. **Forward the packet.** The router reduces the packet’s TTL (IPv4) or Hop Limit (IPv6), puts it in a new link-layer frame suitable for the outgoing link, and sends it onward.

For example, a packet addressed to `192.168.1.50` might match both:

| Route | Where to send it |
|---|---|
| `192.168.1.0/24` | Local network |
| `0.0.0.0/0` — default route | Upstream router |

The `/24` route is more specific, so it wins. The **default route** is used only when no more specific route matches. If there is no matching route, the router drops the packet and may send an “unreachable” message back.

Routes come from directly connected networks, manually defined routes, or routing protocols. Those sources build the routing table; the router then uses that table to forward packets, one hop at a time.