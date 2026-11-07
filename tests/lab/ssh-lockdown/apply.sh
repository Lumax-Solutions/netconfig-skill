ss -tn state established '( sport = :22 )'
sudo nft list chain inet filter input
systemctl is-enabled nftables
sudo cp -a /etc/nftables.conf /root/nftables.conf.bak
sudo sh -c '{ echo "flush ruleset"; nft list ruleset; } > /root/nft-backup.nft'
sudo nft -c -f /root/nft-backup.nft
sudo systemd-run --on-active=10min --unit=nft-rollback /usr/sbin/nft -f /root/nft-backup.nft
systemctl list-timers nft-rollback.timer
sudo tee /root/nft-ssh-lockdown.nft >/dev/null <<'EOF'
flush chain inet filter input
table inet filter {
  chain input {
    ct state established,related accept
    ct state invalid drop
    iif "lo" accept
    meta l4proto { icmp, ipv6-icmp } accept
    ip saddr 198.51.100.10 tcp dport 22 accept
    ip6 saddr 2001:db8:100::10 tcp dport 22 accept
    tcp dport 22 counter drop
    tcp dport { 80, 443 } accept
  }
}
EOF
sudo nft -c -f /root/nft-ssh-lockdown.nft
sudo nft -f /root/nft-ssh-lockdown.nft
sudo nft list chain inet filter input
