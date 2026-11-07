## Restrict new SSH to the admin host (nftables, Ubuntu 24.04)

Linux/nftables is a **Standard**-depth platform in my references. The syntax below is plain nftables 1.0.x, but run the `nft -c` check before every load.

The approach is to replace only the live `inet filter input` chain in a single atomic `nft -f` transaction, with a rollback armed first. `/etc/nftables.conf` doesn't change until your tests pass. I'm not reloading the whole file, because its `flush ruleset` would also wipe any tables that Docker, fail2ban or similar tools have added since boot.

### Assumptions & conflicts

| Item | Found / assumed | Action |
|---|---|---|
| Platform | Ubuntu 24.04, nftables 1.0.9 (given) | None |
| Live ruleset vs file | Assumed: the live `input` chain matches the file you pasted | Phase 0: `nft list chain` must show the same 6 rules. If it differs, stop and send me the output |
| Management path | SSH from 198.51.100.10 / 2001:db8:100::10 (given) | Phase 0: `ss` must show that peer address. If it shows a different one (NAT, or an IPv6 **privacy/temporary** address on the admin host), use the address it shows instead |
| Conflict: `tcp dport 22 accept` | Accepts SSH from anywhere, on both IPv4 and IPv6 | Replaced by the two source-restricted rules (see Change plan) |
| Your current session | Kept alive by the `ct state established,related accept` rule, which stays first | None |
| Other tables (Docker, fail2ban, …) | Unknown | Not touched: only `inet filter input` is flushed and re-filled |
| sshd port | Assumed TCP 22 | If sshd listens on another port, tell me first |
| `nftables.service` | Assumed it loads `/etc/nftables.conf` at boot | Phase 0 `is-enabled` check; the confirm step enables it |
| Out-of-band access | Assumed you have a provider/serial console | Keep it open as a last resort |

### Change plan (chain `inet filter input`)

```text
MODIFY  tcp dport 22 accept  ->  ip saddr 198.51.100.10 tcp dport 22 accept
ADD                              ip6 saddr 2001:db8:100::10 tcp dport 22 accept
ADD     tcp dport 22 counter drop     (after the two allows: counts blocked SSH; policy is drop anyway)
UNCHANGED  established/related, invalid drop, lo, ICMP/ICMPv6, tcp dport {80,443}, policy drop, forward, output
```

### Recovery

- **Backup:** Phase 1 saves the full live ruleset (with `flush ruleset` prepended) to `/root/nft-backup.nft`, and copies the file to `/root/nftables.conf.bak`.
- **Running vs saved:** `nft` changes take effect immediately and live only in the running ruleset. What loads at boot is `/etc/nftables.conf`, and it isn't touched until the confirm step. A reboot before confirming brings back the old rules.
- **Armed rollback:** a `systemd-run` timer reloads the backup after 10 minutes. It runs under systemd, so it still fires if your SSH session drops. A plain `(sleep …) &` job would be killed along with the session. Cancel it with `sudo systemctl stop nft-rollback.timer`.

### Configuration

**Phase 0: read-only checks**

```bash
ss -tn state established '( sport = :22 )'
sudo nft list chain inet filter input
systemctl is-enabled nftables
```

What to look for:
- In the `ss` output, the Peer Address of your session must be `198.51.100.10` or `[2001:db8:100::10]`. If it's anything else, use that address in Phase 2 instead.
- The chain must match your file.
- If `is-enabled` says `disabled`, the confirm step fixes that.

**Phase 1: backup and arm the rollback** (10 minutes)

```bash
sudo cp -a /etc/nftables.conf /root/nftables.conf.bak
sudo sh -c '{ echo "flush ruleset"; nft list ruleset; } > /root/nft-backup.nft'
sudo nft -c -f /root/nft-backup.nft
sudo systemd-run --on-active=10min --unit=nft-rollback /usr/sbin/nft -f /root/nft-backup.nft
systemctl list-timers nft-rollback.timer
```

Check: `nft -c` prints no errors, and `list-timers` shows `nft-rollback.timer` with about 10 minutes left.

**Phase 2: replace the input chain** (management path, one atomic transaction)

```bash
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
```

Check: the chain shows the 8 rules above, the policy is still `drop`, and your current session is still responsive.

Next, **keep this session open** and test from **new** sessions on the admin host (rows 1–2 below), plus rows 3–6 from another machine, all within the 10 minutes. If anything fails, do nothing: the timer restores the old ruleset.

### Acceptance matrix

Replace `<server-ipv4>` / `<server-ipv6>` with the server's public addresses. These commands run on the test machines, not on the server.

| # | Source | Destination | Service | Expected | How to test |
|---|---|---|---|---|---|
| 1 | Admin 198.51.100.10 | server IPv4 | TCP/22 new session | **Allow** | `ssh -4 <user>@<server-ipv4>` |
| 2 | Admin 2001:db8:100::10 | server IPv6 | TCP/22 new session | **Allow** | `ssh -6 <user>@<server-ipv6>`. If it fails, the admin host is probably using a temporary IPv6 source (check `ip -6 addr` / `ss` there) |
| 3 | Any other host (IPv4) | server IPv4 | TCP/22 | **Blocked** | `nc -vz -w5 <server-ipv4> 22` times out; the `tcp dport 22 counter drop` counter rises in `sudo nft list chain inet filter input` |
| 4 | Any other host (IPv6) | server IPv6 | TCP/22 | **Blocked** | `nc -6 -vz -w5 <server-ipv6> 22` times out; the counter rises |
| 5 | Internet (non-admin host) | server IPv4 | TCP/80, 443 | Allow (unchanged) | `curl -4 -I http://<server-ipv4>/` and `curl -4 -kI https://<server-ipv4>/` |
| 6 | Internet (non-admin host) | server IPv6 | TCP/80, 443 | Allow (unchanged) | `curl -6 -I http://[<server-ipv6>]/` and `curl -6 -kI https://[<server-ipv6>]/` |
| 7 | Existing admin session | server | SSH (established) | Keeps working | type in the original window |

### Save & rollback

**After all tests pass** (and before the timer expires), cancel the rollback and persist the config:

```bash
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
```

Check:
- `systemctl list-timers --all | grep nft-rollback` shows nothing.
- `nft -c` printed no errors.
- **Don't** run `systemctl reload nftables` now. The live ruleset is already correct, and a reload would flush other tools' tables.

**Undo:**
- **Phase 2, before confirming:** wait for the timer, or run `sudo nft -f /root/nft-backup.nft`.
- **After confirming:** run `sudo nft -f /root/nft-backup.nft` and `sudo cp /root/nftables.conf.bak /etc/nftables.conf`. This still works from the admin host, because it's allowed under both the old and the new rules.
- **Phase 1:** nothing to undo except `sudo systemctl stop nft-rollback.timer`.

If the admin host's address ever changes, you'll be locked out of SSH. Use the provider console to edit the two `saddr` rules. Optional extra: an `AllowUsers <user>@198.51.100.10 <user>@2001:db8:100::10` line in sshd as a second layer. Ask if you want it.

---
Values filled in: the paste blocks contain no placeholders. The admin addresses 198.51.100.10 and 2001:db8:100::10 come from your message. Only the test commands in the acceptance matrix keep `<server-ipv4>`, `<server-ipv6>` and `<user>`, because your message doesn't give them.
