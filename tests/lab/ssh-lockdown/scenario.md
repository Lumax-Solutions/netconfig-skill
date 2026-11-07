I administer an Ubuntu 24.04 web server (nftables 1.0.9) over SSH. Its firewall is loaded from
/etc/nftables.conf, which currently contains:

```
#!/usr/sbin/nft -f
flush ruleset

table inet filter {
  chain input {
    type filter hook input priority 0; policy drop;
    ct state established,related accept
    ct state invalid drop
    iif "lo" accept
    meta l4proto { icmp, ipv6-icmp } accept
    tcp dport 22 accept
    tcp dport { 80, 443 } accept
  }
  chain forward {
    type filter hook forward priority 0; policy drop;
  }
  chain output {
    type filter hook output priority 0; policy accept;
  }
}
```

I'm connected over SSH from the admin host 198.51.100.10 (IPv6 2001:db8:100::10). Restrict NEW SSH
connections to that admin host only (IPv4 and IPv6), and keep the public website (TCP 80/443)
reachable over IPv4 and IPv6 from anywhere. I don't want to lock myself out.
