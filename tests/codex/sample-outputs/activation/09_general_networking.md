TCP and UDP are two ways apps send data across a network, such as the internet.

**TCP is like sending numbered parcels with delivery confirmation.** It checks that data arrives and puts it in the correct order. If something goes missing, it sends it again.

For example, when downloading a document, you need every piece to arrive correctly. Waiting a little longer is better than ending up with a broken file.

**UDP is like making announcements over a loudspeaker.** It sends data without checking whether everyone received it. It doesn’t automatically resend missing pieces or guarantee their order.

For example, in an online game, a fresh update about a player’s position can be more useful than waiting for an old, missing update.

| | TCP | UDP |
|---|---|---|
| Delivery | Checks delivery and retries missing data | No built-in delivery confirmation or retries |
| Order | Delivers data in order | Data may arrive out of order |
| Tradeoff | Extra checking can add delay | Less overhead, useful when timely updates matter |
| Common uses | Web pages, email, file downloads | Live calls, online games, DNS lookups |

A useful rule of thumb: **TCP prioritizes complete, ordered delivery; UDP gives apps more control over speed and handling missing data.** Apps using UDP can add their own reliability features when needed.