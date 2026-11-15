"""Offline tests for the desktop app: secret removal, prompt building, vendor guessing, and a full
streamed chat through the HTTP server against a fake OpenAI-compatible model. Run: python app/test_app.py"""
import json
import os
import sys
import tempfile
import threading
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

os.environ["XDG_CONFIG_HOME"] = os.environ["APPDATA"] = tempfile.mkdtemp()
sys.path.insert(0, str(Path(__file__).parent))
import netconfig_app as A  # noqa: E402
from sanitize import restore_pairs, sanitize  # noqa: E402

failures = 0


def check(name, ok):
    global failures
    print(("PASS " if ok else "FAIL ") + name)
    failures += not ok


SAMPLE = """hostname R1
enable secret 9 $9$abcdefghijklmnop$qrstuvwxyz0123456789ABCDEFG
username admin privilege 15 secret 5 $1$salt$hashhashhash
snmp-server community S3cretComm RO
crypto isakmp key MyPsk123 address 203.0.113.9
line vty 0 4
 password 7 0822455D0A16
config system admin
    edit "admin"
        set password ENC SH2abcdefghijklmnopqrstuvwxyz0123456789
    next
end
set security ike policy P pre-shared-key ascii-text "$9$Ab1Cd2Ef3"
/ppp secret add name=x password=hunter2 service=pptp
/ip firewall filter add chain=input action=accept
interface GigabitEthernet0/0
 ip address 41.33.77.10 255.255.255.0
"""
clean, found, _ = sanitize(SAMPLE, mask_public_ips=True)
for secret in ["$9$abcdefghijklmnop", "$1$salt$", "S3cretComm", "MyPsk123", "0822455D0A16", "SH2abcdef", "$9$Ab1Cd2Ef3", "hunter2"]:
    check(f"sanitize removes {secret}", secret not in clean)
for keep in ["hostname R1", "/ppp secret add name=x", "chain=input action=accept", "255.255.255.0", "line vty 0 4"]:
    check(f"sanitize keeps '{keep}'", keep in clean)
check("public IP mapped to documentation range", "41.33.77.10" not in clean and "198.51.100.10" in clean)
check("findings reported", len(found) >= 8)
more, _, _ = sanitize('ntp authentication-key 1 md5 NtpKey123\n<entry name="a"><phash>$1$abcdefgh$Q1w2E3r4</phash></entry>\n'
                   'ip ospf message-digest-key 1 md5 OspfKey9')
check("NTP key removed (not the word md5)", "NtpKey123" not in more and "md5 <REDACTED" in more)
check("Palo Alto phash removed, XML kept", "Q1w2E3r4" not in more and "</phash></entry>" in more)
check("OSPF MD5 key removed", "OspfKey9" not in more)
same, _, _ = sanitize("snmp-server community abc RO\nsnmp-server community abc RW")
check("same secret -> same token", same.count("<REDACTED-1>") == 2)

# ---- names and public IPs (privacy options)
CISCO = """hostname CAI-SV-RTR01
ip domain name corp.acme-egypt.com
username jsmith privilege 15 secret 9 $9$zzzzzzzzzzzz$yyyyyyyyyyyy
banner motd ^C
ACME Egypt - authorized access only
^C
snmp-server location Smart Village B12, Giza
snmp-server contact noc@acme-egypt.com
interface GigabitEthernet0/0/0
 description Vodafone circuit VF-4471-22981
 ip address 41.33.77.10 255.255.255.252
interface GigabitEthernet0/0/1
 description WAN to ISP
 ip address 10.10.0.1 255.255.255.0
ip route 0.0.0.0 0.0.0.0 41.33.77.9
ip name-server 8.8.8.8
crypto isakmp key K3y!789 address 102.40.1.2
ipv6 address 2a00:1450:4001:82a::1/64
logging host vpn.corp.acme-egypt.com
CAI-SV-RTR01# show ip route
"""
c, f, st = sanitize(CISCO, mask_public_ips=True, hide_names=True)
for gone in ["CAI-SV-RTR01", "acme-egypt", "jsmith", "ACME Egypt", "Smart Village", "noc@", "Vodafone", "41.33.77", "102.40.1.2",
             "2a00:1450", "K3y!789"]:
    check(f"names/IPs: '{gone}' hidden", gone not in c)
for kept in ["description WAN to ISP", "10.10.0.1 255.255.255.0", "ip name-server 8.8.8.8", "interface GigabitEthernet0/0/0",
             "255.255.255.252", "banner motd ^C"]:
    check(f"names/IPs: '{kept}' kept", kept in c)
check("names: hostname also replaced in the prompt", "HOST-1# show ip route" in c)
check("names: FQDN under a hidden domain", "vpn.domain1.example" in c)
check("IPs: same /24 stays the same /24 (gateway still in the subnet)",
      "ip address 198.51.100.10 255.255.255.252" in c and "0.0.0.0 0.0.0.0 198.51.100.9" in c)
check("IPs: another public network gets another documentation network", "192.0.2.2" not in c and "203.0.113.2" in c)
check("IPv6: global address mapped into 2001:db8::/32, interface ID kept", "2001:db8:1:82a::1/64" in c)
pairs = dict(restore_pairs(st))
check("restore: placeholders map back to the real values",
      pairs.get("HOST-1") == "CAI-SV-RTR01" and pairs.get("198.51.100.9") == "41.33.77.9" and pairs.get("domain1.example") == "corp.acme-egypt.com")
check("restore: secrets are never restorable", not any(k.startswith("<REDACTED") for k in pairs))
c2, _, st2 = sanitize("CAI-SV-RTR01 still can't reach 41.33.77.9; enable secret 9 $9$newnewnewnew$aaaa", True, True, state=st)
check("state: follow-up reuses the same placeholders", "HOST-1 still can't reach 198.51.100.9" in c2)
check("state: secret numbering continues across messages", "<REDACTED-3>" in c2)
FORTI = 'config system global\n    set hostname "ACME-FW1"\nend\nconfig system admin\n    edit "m.hassan"\n    next\nend\n' \
        'config firewall address\n    edit "WEB"\n        set comment "payroll server"\n    next\nend\n'
cf, _, _ = sanitize(FORTI, hide_names=True)
check("FortiGate: hostname, admin user and comment hidden", all(x not in cf for x in ["ACME-FW1", "m.hassan", "payroll"]))
check("FortiGate: object name and syntax kept", 'edit "WEB"' in cf and 'set hostname "HOST-1"' in cf)
JUN = 'set system host-name acme-srx1\nset system login user tamer class super-user\nset interfaces ge-0/0/0 description "Etisalat EG-99812"\n'
cj, _, _ = sanitize(JUN, hide_names=True)
check("Junos: host, user, description hidden", all(x not in cj for x in ["acme-srx1", "tamer", "Etisalat"]))
MT = '/system identity set name=ACME-Giza\n/user add name=karim group=full\n/ip address add address=10.0.0.1/24 interface=ether2 comment="Giza office"\n'
cm, _, _ = sanitize(MT, hide_names=True)
check("MikroTik: identity, user, comment hidden", all(x not in cm for x in ["ACME-Giza", "karim", "Giza office"]))
check("off by default: nothing but secrets changes", sanitize(CISCO)[0].count("CAI-SV-RTR01") == 2)
# the skill's own reference examples must survive name hiding (only names, never syntax)
import re as _re  # noqa: E402
bad = []
for ref in sorted((A.SKILL_DIR / "references").glob("*.md")):
    for block in _re.findall(r"```[^\n]*\n(.*?)```", ref.read_text(encoding="utf-8"), _re.S):
        out, fnd, _ = sanitize(block, mask_public_ips=True, hide_names=True)
        bad += [x for x in fnd if x["kind"] in ("secret", "user", "email", "contact", "location", "banner")]
check("reference examples: no false secrets/users when hiding names", not bad)

prompt, refs = A.build_system_prompt(["fortigate"], "change", has_config=True)
check("prompt has core skill", "network-config skill: SKILL.md" in prompt and "name: network-config" not in prompt)
check("prompt loads fortigate + change-workflow refs", {"fortigate", "change-workflow", "sanitizing-configs"} <= set(refs))
check("vendor guess: FortiGate", A.guess_vendors("config firewall policy\n    edit 1") == ["fortigate"])
check("vendor guess: MikroTik", A.guess_vendors("/ip address add address=1.1.1.1/24") == ["mikrotik"])


class FakeModel(BaseHTTPRequestHandler):
    seen = {}

    def log_message(self, *a):
        pass

    def do_GET(self):
        b = json.dumps({"data": [{"id": "fake-model"}]}).encode()
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b)

    def do_POST(self):
        FakeModel.seen = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        self.send_response(200)
        self.end_headers()
        for d in ({"reasoning_content": "think"}, {"content": "## Plan\n"}, {"content": "```text\nshow version\n```"}):
            self.wfile.write(b"data: " + json.dumps({"choices": [{"delta": d}]}).encode() + b"\n\n")
        self.wfile.write(b"data: [DONE]\n\n")


model = ThreadingHTTPServer(("127.0.0.1", 0), FakeModel)
app = ThreadingHTTPServer(("127.0.0.1", 0), A.Handler)
for s in (model, app):
    threading.Thread(target=s.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{app.server_port}"


def post(path, body, headers=None):
    req = urllib.request.Request(base + path, json.dumps(body).encode(), dict({"Content-Type": "application/json"}, **(headers or {})))
    return urllib.request.urlopen(req, timeout=10)


post("/api/settings", {"preset": "custom", "base_url": f"http://127.0.0.1:{model.server_port}/v1", "model": "fake-model"})
r1 = json.load(post("/api/sanitize", {"text": "hostname BR-RTR-77\nip route 0.0.0.0 0.0.0.0 41.33.77.9", "mask_public_ips": True, "hide_names": True}))
r2 = json.load(post("/api/sanitize", {"text": "BR-RTR-77 lost 41.33.77.9", "mask_public_ips": True, "hide_names": True, "state": r1["state"]}))
check("API sanitize: returns state + restore pairs", "state" in r1 and ["HOST-1", "BR-RTR-77"] in r1["restore"])
check("API sanitize: state keeps placeholders across calls", r2["text"] == "HOST-1 lost 198.51.100.9")
check("system prompt explains placeholders", "HOST-n" in A.APP_PREAMBLE and "198.51.100.0/24" in A.APP_PREAMBLE)
check("models listed", json.load(post("/api/models", {}))["models"] == ["fake-model"])
events = [json.loads(line[5:]) for line in post("/api/chat", {"vendors": ["unknown"], "task": "fix", "messages": [
    {"role": "user", "content": "VPN down\n```text\nconfig vpn ipsec phase1-interface\n    edit x\n```"}]}).read().decode().split("\n\n") if line.startswith("data:")]
text = "".join(e["text"] for e in events if e["type"] == "delta")
check("chat streams answer", text == "## Plan\n```text\nshow version\n```")
check("chat streams reasoning separately", any(e["type"] == "thinking" for e in events))
check("chat ends with done", events[-1]["type"] == "done")
check("system prompt sent first", FakeModel.seen["messages"][0]["role"] == "system")
check("'Not sure' + FortiGate config loads fortigate.md", "references/fortigate.md" in FakeModel.seen["messages"][0]["content"])
try:
    post("/api/settings", {}, {"Origin": "http://evil.example"})
    check("other websites are refused", False)
except urllib.error.HTTPError as e:
    check("other websites are refused", e.code == 403)


class StrictModel(BaseHTTPRequestHandler):  # like newer Claude models: rejects `temperature`
    def log_message(self, *a):
        pass

    def do_POST(self):
        b = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if "temperature" in b:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'{"type":"error","error":{"message":"`temperature` is deprecated for this model."}}')
            return
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'data: {"type":"content_block_delta","delta":{"type":"text_delta","text":"ok"}}\n\n')


strict = ThreadingHTTPServer(("127.0.0.1", 0), StrictModel)
threading.Thread(target=strict.serve_forever, daemon=True).start()
got = []
A.stream_chat({"preset": "anthropic", "base_url": f"http://127.0.0.1:{strict.server_port}/v1", "api_key": "k", "model": "m"},
              "sys", [{"role": "user", "content": "hi"}], lambda k, t: got.append(t))
check("retries without temperature when the model rejects it", got == ["ok"])

print(f"\n{'All tests passed' if not failures else f'{failures} FAILED'}")
sys.exit(1 if failures else 0)
