# Lab tests

Disposable Linux firewall labs that **apply real configurations and test real traffic**, built
from Linux network namespaces. Nothing outside the lab's own namespaces is touched. They run in CI
on every push (`.github/workflows/validate.yml`, job *Linux firewall lab*).

Requirements: Linux, root, `iproute2`, `nftables`, `iptables`, Python 3.12+.

```bash
sudo python3 tests/lab/reference_examples.py          # the Linux examples in references/host-cloud.md
sudo python3 tests/lab/ssh-lockdown/lab.py             # the SSH-lockdown demo (add --require-ipv6 in CI)
```

## SSH-lockdown demo

**The question:** *can an agent tighten SSH on a live server without locking you out?*

1. [`ssh-lockdown/scenario.md`](ssh-lockdown/scenario.md) is the exact prompt given to an agent
   with the skill installed, including the server's current `/etc/nftables.conf`
   ([`start.nft`](ssh-lockdown/start.nft): SSH open to everyone, web open).
2. [`ssh-lockdown/skill-answer.md`](ssh-lockdown/skill-answer.md) is the skill's full answer.
   [`apply.sh`](ssh-lockdown/apply.sh) and [`confirm.sh`](ssh-lockdown/confirm.sh) are its
   commands, **copied verbatim** in paste order: backup → arm a 10-minute rollback timer →
   apply; then, after testing, cancel the timer and persist.
3. [`ssh-lockdown/lab.py`](ssh-lockdown/lab.py) builds three hosts on one network segment and
   checks the answer from separate clients:

| Host | IPv4 | IPv6 | Role |
|---|---|---|---|
| server | 192.0.2.10 | 2001:db8:1::10 | firewall under test, listeners on TCP 22/80/443 |
| admin | 198.51.100.10 | 2001:db8:100::10 | the admin host that must keep SSH |
| other | 203.0.113.50 | 2001:db8:200::50 | an unauthorized host and public web client |

| Phase | Checks |
|---|---|
| Starting state | SSH open from both hosts; web open (IPv4 + IPv6) |
| Apply (timer armed) | an SSH session opened *before* the change keeps working; new SSH from admin works; new SSH from other is **blocked**; HTTP/HTTPS still open — each over IPv4 and IPv6 |
| Let the timer expire | original access is **restored** automatically (SSH from other works again) |
| Apply + confirm | the restriction stays after the timer would have fired |
| Reload saved config | the restriction persists (as after a reboot) |

### How the lab maps the answer onto the test machine

The answer is written for a real server, so the lab adapts only the environment, never the
commands' logic:
- `/etc/nftables.conf` and `/root/...` point to a temporary directory.
- `sleep N` is capped to 4 seconds and `systemd-run --on-active=… --unit=X cmd` becomes a
  4-second background job that `systemctl stop X.timer` cancels (no systemd in the lab), so the
  10-minute rollback fires in seconds.
- `sudo` runs the command directly; `systemctl enable` is skipped.

### Results

| Where | nftables | Kernel | Checks |
|---|---|---|---|
| Development sandbox (IPv4 only, no IPv6 in its kernel) | 1.0.9 | 6.18 | 24/24 |
| GitHub Actions `ubuntu-24.04` (IPv4 + IPv6, `--require-ipv6`) | Ubuntu 24.04 package | runner kernel | 44/44, every push — see the latest [CI run](https://github.com/Lumax-Solutions/netconfig-skill/actions/workflows/validate.yml) |

The lab also **fails** a broken answer: a variant that applies the same rules without arming the
rollback timer fails the "original access restored" check.

### Test your own candidate

```bash
sudo python3 tests/lab/ssh-lockdown/lab.py --apply my-apply.sh --confirm my-confirm.sh
```

Answers from other agents or skill versions can be compared on the same lab — please share results.

## Reference examples

[`reference_examples.py`](reference_examples.py) extracts the nftables and iptables examples
from `skills/network-config/references/host-cloud.md`, loads each into the lab server, and checks
that SSH works only from the admin network (`10.0.99.0/24`) while HTTP/HTTPS stay open.
If someone edits those examples, CI tests the new text automatically.
