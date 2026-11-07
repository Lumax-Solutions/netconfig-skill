#!/usr/bin/env python3
"""Load the Linux firewall examples from skills/network-config/references/host-cloud.md into a
throwaway network namespace and check that they are accepted and behave as described:
the nftables and iptables examples allow SSH only from the admin network and HTTP/HTTPS from
anywhere. Requires Linux, root, iproute2, nftables and iptables. Run: sudo python3 reference_examples.py
"""
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REF = Path(__file__).resolve().parents[2] / "skills" / "network-config" / "references" / "host-cloud.md"
SRV, ADM, OTH = "ncr-srv", "ncr-adm", "ncr-oth"
ADDR = {SRV: "192.0.2.10", ADM: "10.0.99.5", OTH: "203.0.113.50"}
results = []


def sh(cmd, check=True):
    r = subprocess.run(cmd, shell=True, text=True, capture_output=True)
    if check and r.returncode:
        raise RuntimeError(f"{cmd}\n{r.stdout}{r.stderr}")
    return r


def block_after(heading):
    text = REF.read_text(encoding="utf-8")
    i = text.index(heading)
    m = re.search(r"```[a-z]*\n(.*?)```", text[i:], re.S)
    return m.group(1)


def topology():
    teardown()
    sh(f"ip netns add {SRV}")
    for c in (ADM, OTH):
        sh(f"ip netns add {c}")
        sh(f"ip link add {c}0 netns {c} type veth peer name {c}s netns {SRV}")
        sh(f"ip -n {c} addr add {ADDR[c]}/32 dev {c}0; ip -n {c} link set {c}0 up; ip -n {c} link set lo up")
        sh(f"ip -n {c} route add {ADDR[SRV]}/32 dev {c}0")
        sh(f"ip -n {SRV} addr add {ADDR[SRV]}/32 dev {c}s; ip -n {SRV} link set {c}s up")
        sh(f"ip -n {SRV} route add {ADDR[c]}/32 dev {c}s")
    sh(f"ip -n {SRV} link set lo up")


def teardown():
    for n in (SRV, ADM, OTH):
        sh(f"ip netns del {n} 2>/dev/null", check=False)


def listeners():
    code = ("import socket,threading\n"
            "def s(p):\n"
            " k=socket.socket();k.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);k.bind(('0.0.0.0',p));k.listen(8)\n"
            " while True:\n  c,_=k.accept();c.sendall(b'ok');c.close()\n"
            "[threading.Thread(target=s,args=(p,),daemon=True).start() for p in (22,80,443)]\n"
            "threading.Event().wait()\n")
    return subprocess.Popen(["ip", "netns", "exec", SRV, sys.executable, "-c", code])


def reach(src, port):
    code = f"import socket,sys\ns=socket.create_connection(('{ADDR[SRV]}',{port}),timeout=1.5)\nsys.exit(0 if s.recv(2)==b'ok' else 1)"
    return subprocess.run(["ip", "netns", "exec", src, sys.executable, "-c", code], capture_output=True).returncode == 0


def expect(name, got, want):
    ok = got == want
    results.append(ok)
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}: expected {'yes' if want else 'no'}, got {'yes' if got else 'no'}")


def matrix(label):
    print(label)
    expect("SSH from admin network 10.0.99.0/24", reach(ADM, 22), True)
    expect("SSH from another host", reach(OTH, 22), False)
    expect("HTTPS from another host", reach(OTH, 443), True)
    expect("HTTP from another host", reach(OTH, 80), True)


def main():
    if os.geteuid() != 0:
        sys.exit("needs root: run with sudo")
    topology()
    srv = listeners()
    try:
        import time; time.sleep(1)
        # nftables example
        nft = block_after("**nftables (modern Linux")
        with tempfile.NamedTemporaryFile("w", suffix=".nft", delete=False) as f:
            f.write(nft)
        r = sh(f"ip netns exec {SRV} nft -c -f {f.name}", check=False)
        expect("nftables example passes `nft -c`", r.returncode == 0, True)
        sh(f"ip netns exec {SRV} nft -f {f.name}")
        matrix("nftables example loaded:")
        sh(f"ip netns exec {SRV} nft flush ruleset")
        # iptables example (each command line, persistence line skipped)
        ipt = [l for l in block_after("**iptables (legacy):**").splitlines()
               if l.strip().startswith("iptables ")]
        ok = all(sh(f"ip netns exec {SRV} {l}", check=False).returncode == 0 for l in ipt)
        expect("iptables example commands run", ok, True)
        matrix("iptables example loaded:")
    finally:
        srv.kill()
        teardown()
    print(f"RESULT: {sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
