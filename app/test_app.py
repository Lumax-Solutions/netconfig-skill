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
from sanitize import sanitize  # noqa: E402

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
 ip address 8.8.4.4 255.255.255.0
"""
clean, found = sanitize(SAMPLE, mask_public_ips=True)
for secret in ["$9$abcdefghijklmnop", "$1$salt$", "S3cretComm", "MyPsk123", "0822455D0A16", "SH2abcdef", "$9$Ab1Cd2Ef3", "hunter2"]:
    check(f"sanitize removes {secret}", secret not in clean)
for keep in ["hostname R1", "/ppp secret add name=x", "chain=input action=accept", "255.255.255.0", "line vty 0 4"]:
    check(f"sanitize keeps '{keep}'", keep in clean)
check("public IP mapped to documentation range", "8.8.4.4" not in clean and "203.0.113." in clean)
check("findings reported", len(found) >= 8)
more, _ = sanitize('ntp authentication-key 1 md5 NtpKey123\n<entry name="a"><phash>$1$abcdefgh$Q1w2E3r4</phash></entry>\n'
                   'ip ospf message-digest-key 1 md5 OspfKey9')
check("NTP key removed (not the word md5)", "NtpKey123" not in more and "md5 <REDACTED" in more)
check("Palo Alto phash removed, XML kept", "Q1w2E3r4" not in more and "</phash></entry>" in more)
check("OSPF MD5 key removed", "OspfKey9" not in more)
same, _ = sanitize("snmp-server community abc RO\nsnmp-server community abc RW")
check("same secret -> same token", same.count("<REDACTED-1>") == 2)

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
