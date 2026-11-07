sudo systemctl stop nft-rollback.timer
sudo tee /root/nftables.conf.new >/dev/null <<'EOF'
#!/usr/sbin/nft -f
flush ruleset

table inet filter {
  chain input {
    type filter hook input priority 0; policy drop;
    ct state established,related accept
    ct state invalid drop
    iif "lo" accept
    meta l4proto { icmp, ipv6-icmp } accept
    ip saddr 198.51.100.10 tcp dport 22 accept
    ip6 saddr 2001:db8:100::10 tcp dport 22 accept
    tcp dport 22 counter drop
    tcp dport { 80, 443 } accept
  }
  chain forward {
    type filter hook forward priority 0; policy drop;
  }
  chain output {
    type filter hook output priority 0; policy accept;
  }
}
EOF
sudo nft -c -f /root/nftables.conf.new
sudo cp /root/nftables.conf.new /etc/nftables.conf
sudo systemctl enable nftables
