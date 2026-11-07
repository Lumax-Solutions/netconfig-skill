#!/usr/bin/env python3
"""SSH-lockdown lab: apply a firewall change on a disposable Linux "server" and check it from
separate clients over IPv4 and IPv6, including what happens when the rollback timer expires.

Requires Linux, root (network namespaces), iproute2, nftables and Python 3.12+. Nothing outside
the lab's own network namespaces is touched.

  sudo python3 lab.py                      # test the committed skill answer (apply.sh / confirm.sh)
  sudo python3 lab.py --apply X --confirm Y # test any other candidate change

Topology (one L2 segment):
  server  192.0.2.10      2001:db8:1::10     firewall under test, TCP listeners on 22, 80, 443
  admin   198.51.100.10   2001:db8:100::10   the allowed admin host
  other   203.0.113.50    2001:db8:200::50   an unauthorized host / public web client
"""
import argparse
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import textwrap
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
NS = {
    "server": ("192.0.2.10", "2001:db8:1::10"),
    "admin": ("198.51.100.10", "2001:db8:100::10"),
    "other": ("203.0.113.50", "2001:db8:200::50"),
}
PREFIX = "ncl"  # namespace prefix, so a crashed run is easy to spot and clean
SHIM_SLEEP_MAX = 4  # seconds: any `sleep N` in the candidate is capped to this in the lab
results = []
IPV6 = os.path.exists("/proc/sys/net/ipv6")


def sh(cmd, check=True, **kw):
    r = subprocess.run(cmd, shell=isinstance(cmd, str), text=True, capture_output=True, **kw)
    if check and r.returncode:
        raise RuntimeError(f"command failed ({r.returncode}): {cmd}\n{r.stdout}{r.stderr}")
    return r


def ns(name):
    return f"{PREFIX}-{name}"


def netns_exec(name, cmd, **kw):
    return sh(["ip", "netns", "exec", ns(name)] + cmd, **kw)


def cleanup():
    sh(f"ip link del {PREFIX}-br 2>/dev/null", check=False)
    for n in list(NS) + ["sw"]:
        sh(f"ip netns del {ns(n)} 2>/dev/null", check=False)


def build():
    cleanup()
    sh(f"ip netns add {ns('sw')}")
    netns_exec("sw", ["ip", "link", "add", "br0", "type", "bridge"])
    netns_exec("sw", ["ip", "link", "set", "br0", "up"])
    for n, (v4, v6) in NS.items():
        sh(f"ip netns add {ns(n)}")
        sh(f"ip link add {n}0 netns {ns(n)} type veth peer name {n}p netns {ns('sw')}")
        netns_exec("sw", ["ip", "link", "set", f"{n}p", "master", "br0", "up"])
        if IPV6:
            netns_exec(n, ["sysctl", "-qw", "net.ipv6.conf.all.disable_ipv6=0"])
        netns_exec(n, ["ip", "link", "set", "lo", "up"])
        netns_exec(n, ["ip", "addr", "add", f"{v4}/32", "dev", f"{n}0"])
        if IPV6:
            netns_exec(n, ["ip", "addr", "add", f"{v6}/128", "dev", f"{n}0", "nodad"])
        netns_exec(n, ["ip", "link", "set", f"{n}0", "up"])
        # every other host is on-link (one L2 segment, different subnets)
        for m, (w4, w6) in NS.items():
            if m != n:
                netns_exec(n, ["ip", "route", "add", f"{w4}/32", "dev", f"{n}0"])
                if IPV6:
                    netns_exec(n, ["ip", "-6", "route", "add", f"{w6}/128", "dev", f"{n}0"])


SERVER = textwrap.dedent("""
    import socket, threading
    def serve(port):
        try:
            s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
            s.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
            addr = "::"
        except OSError:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            addr = "0.0.0.0"
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((addr, port)); s.listen(16)
        while True:
            c, _ = s.accept()
            threading.Thread(target=echo, args=(c,), daemon=True).start()
    def echo(c):
        while True:
            d = c.recv(64)
            if not d: break
            c.sendall(d)
    for p in (22, 80, 443):
        threading.Thread(target=serve, args=(p,), daemon=True).start()
    threading.Event().wait()
""")


def start_listeners():
    return subprocess.Popen(["ip", "netns", "exec", ns("server"), sys.executable, "-c", SERVER])


def can_connect(src, family, port, timeout=1.5):
    dst = NS["server"][0 if family == 4 else 1]
    code = (f"import socket,sys\n"
            f"s=socket.create_connection(('{dst}',{port}),timeout={timeout})\n"
            f"s.sendall(b'hi'); sys.exit(0 if s.recv(8)==b'hi' else 1)")
    return netns_exec(src, [sys.executable, "-c", code], check=False).returncode == 0


class HeldSession:
    """A TCP session opened from the admin host before the change (stands in for the live SSH session)."""

    def __init__(self, family=4):
        own = os.open("/proc/self/ns/net", os.O_RDONLY)
        target = os.open(f"/var/run/netns/{ns('admin')}", os.O_RDONLY)
        os.setns(target, os.CLONE_NEWNET)
        try:
            self.sock = socket.create_connection((NS["server"][0 if family == 4 else 1], 22), timeout=2)
        finally:
            os.setns(own, os.CLONE_NEWNET)
            os.close(own); os.close(target)

    def alive(self):
        try:
            self.sock.sendall(b"hi")
            return self.sock.recv(8) == b"hi"
        except OSError:
            return False


def check(name, got, want):
    ok = got == want
    results.append((name, want, got, ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}: expected {'yes' if want else 'no'}, got {'yes' if got else 'no'}")
    return ok


def access_matrix(phase, ssh_other_expected, held=None):
    print(f"\n{phase}")
    if held is not None:
        check("existing admin SSH session keeps working", held.alive(), True)
    for fam in ((4, 6) if IPV6 else (4,)):
        check(f"new SSH from admin host (IPv{fam})", can_connect("admin", fam, 22), True)
        check(f"new SSH from other host (IPv{fam})", can_connect("other", fam, 22), ssh_other_expected)
        check(f"HTTPS from other host (IPv{fam})", can_connect("other", fam, 443), True)
        check(f"HTTP from other host (IPv{fam})", can_connect("other", fam, 80), True)


def make_workdir():
    """Files the candidate commands expect, mapped into a temp dir, plus shims for sleep/systemctl/sudo."""
    work = Path(tempfile.mkdtemp(prefix="ncl-lab-"))
    (work / "etc").mkdir()
    shutil.copy(HERE / "start.nft", work / "etc" / "nftables.conf")
    shims = work / "bin"
    shims.mkdir()
    (shims / "sleep").write_text(textwrap.dedent(f"""\
        #!/bin/sh
        # lab shim: cap long sleeps so rollback timers fire within seconds
        n=$(printf '%s' "$1" | tr -dc '0-9'); [ -z "$n" ] && n={SHIM_SLEEP_MAX}
        [ "$n" -gt {SHIM_SLEEP_MAX} ] && n={SHIM_SLEEP_MAX}
        exec /bin/sleep "$n"
        """))
    (shims / "systemd-run").write_text(textwrap.dedent(f"""\
        #!/bin/sh
        # lab shim for transient timers: systemd-run --on-active=<t> --unit=<name> <command...>
        # Runs <command> after the (capped) delay; `systemctl stop <name>[.timer]` cancels it.
        unit=transient; delay={SHIM_SLEEP_MAX}
        while [ $# -gt 0 ]; do
          case "$1" in
            --on-active=*|--on-calendar=*|--on-boot=*) shift ;;
            --unit=*) unit="${{1#--unit=}}"; shift ;;
            --unit) unit="$2"; shift 2 ;;
            --*) shift ;;
            *) break ;;
          esac
        done
        mkdir -p {work}/units
        setsid sh -c '/bin/sleep {SHIM_SLEEP_MAX}; exec "$@"' rollback "$@" >/dev/null 2>&1 &
        echo $! > "{work}/units/$unit.pid"
        echo "Running timer as unit: $unit.timer (lab)"
        """))
    (shims / "systemctl").write_text(textwrap.dedent(f"""\
        #!/bin/sh
        # lab shim: stop/cancel transient units, answer is-enabled, skip the rest
        case "$1" in
          stop|kill)
            for u in "$@"; do
              n="${{u%.timer}}"; n="${{n%.service}}"
              [ -f "{work}/units/$n.pid" ] && kill "$(cat {work}/units/$n.pid)" 2>/dev/null && rm -f "{work}/units/$n.pid" && echo "(lab) stopped $u"
            done ;;
          is-enabled) echo enabled ;;
          list-timers) ls {work}/units 2>/dev/null ;;
          *) echo "(lab: systemctl $* skipped)" ;;
        esac
        exit 0
        """))
    (shims / "sudo").write_text("#!/bin/sh\nexec \"$@\"\n")
    for f in shims.iterdir():
        f.chmod(0o755)
    return work


def localize(script, work):
    # Map the real paths used in the answer onto the lab's temp dir.
    s = script.replace("/etc/nftables.conf", f"{work}/etc/nftables.conf")
    return s.replace("/root/", f"{work}/").replace("~/", f"{work}/")


def run_in_server(script_path, work, label):
    script = localize(Path(script_path).read_text(), work)
    env = dict(os.environ, PATH=f"{work}/bin:{os.environ.get('PATH', '/usr/sbin:/usr/bin:/sbin:/bin')}", HOME=str(work))
    # Run like a pasted SSH session: one shell, background jobs survive after the script returns.
    # Output goes to a file, not a pipe, so a backgrounded rollback timer can't hold us up.
    log = work / f"{label.split()[0].lower()}.log"
    with open(log, "w") as out:
        p = subprocess.run(["ip", "netns", "exec", ns("server"), "setsid", "bash", "-c", script],
                           cwd=work, env=env, stdin=subprocess.DEVNULL, stdout=out, stderr=subprocess.STDOUT, timeout=60)
    print(f"\n{label}: exit {p.returncode}")
    if p.returncode:
        print(log.read_text()[-2000:])
    return p.returncode == 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", default=str(HERE / "apply.sh"), help="commands that make the change and arm the rollback")
    ap.add_argument("--confirm", default=str(HERE / "confirm.sh"), help="commands that keep the change (cancel the rollback, persist)")
    ap.add_argument("--require-ipv6", action="store_true", help="fail instead of skipping IPv6 checks when the kernel has no IPv6 (use in CI)")
    args = ap.parse_args()
    if os.geteuid() != 0:
        sys.exit("needs root (network namespaces): run with sudo")
    for tool in ("ip", "nft", "setsid"):
        if not shutil.which(tool):
            sys.exit(f"missing tool: {tool}")
    print(f"nftables: {sh('nft --version').stdout.strip()}  |  kernel: {os.uname().release}  |  IPv6: {'yes' if IPV6 else 'NOT AVAILABLE'}")
    if not IPV6:
        if args.require_ipv6:
            sys.exit("IPv6 not available in this kernel and --require-ipv6 was given")
        print("WARNING: this kernel has no IPv6; IPv6 checks are SKIPPED. Run on a host with IPv6 for full coverage.")
    build()
    listeners = start_listeners()
    time.sleep(1)
    try:
        # --- Run 1: apply, verify, then let the rollback timer expire ---
        work = make_workdir()
        netns_exec("server", ["nft", "-f", str(work / "etc" / "nftables.conf")])
        access_matrix("Starting state (SSH open to everyone)", ssh_other_expected=True)
        held = HeldSession()
        check("apply commands run without error", run_in_server(args.apply, work, "Apply (rollback armed)"), True)
        time.sleep(0.5)
        access_matrix("After the change, before confirming", ssh_other_expected=False, held=held)
        time.sleep(SHIM_SLEEP_MAX + 3)
        access_matrix("Rollback timer expired without confirming: original access must be back",
                      ssh_other_expected=True)

        # --- Run 2: apply, confirm, and check the change stays after the timer would have fired ---
        work2 = make_workdir()
        netns_exec("server", ["nft", "-f", str(work2 / "etc" / "nftables.conf")])
        check("apply commands run without error (run 2)", run_in_server(args.apply, work2, "Apply again"), True)
        time.sleep(0.5)
        check("confirm commands run without error", run_in_server(args.confirm, work2, "Confirm"), True)
        time.sleep(SHIM_SLEEP_MAX + 3)
        access_matrix("Confirmed: restriction must stay after the timer would have fired",
                      ssh_other_expected=False)
        print("\nReloading the saved /etc/nftables.conf (as after a reboot)")
        netns_exec("server", ["nft", "-f", str(work2 / "etc" / "nftables.conf")])
        access_matrix("After reload from the saved file: restriction persists", ssh_other_expected=False)
    finally:
        listeners.kill()
        cleanup()
    failed = [r for r in results if not r[3]]
    print(f"\nRESULT: {len(results) - len(failed)}/{len(results)} checks passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
