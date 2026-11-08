#!/usr/bin/env python3
"""NetConfig Assistant: a local web app that puts the network-config skill behind a simple,
guided interface. Standard library only. Advice only: it never connects to network devices.

Run:  python netconfig_app.py      (or double-click start-windows.bat / start-mac-linux.sh)
Then the browser opens at http://127.0.0.1:8765

AI backends: any OpenAI-compatible server (llama.cpp llama-server, llama-swap, Ollama, LM Studio,
vLLM, OpenAI, DeepInfra, OpenRouter …) or the Anthropic API.
"""
import json
import os
import re
import socket
import sys
import threading
import urllib.error
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from sanitize import sanitize

APP_DIR = Path(__file__).resolve().parent
STATIC = APP_DIR / "static"
SKILL_DIR = Path(os.environ.get("NETCONFIG_SKILL_DIR", APP_DIR.parent / "skills" / "network-config")).resolve()
APP_VERSION = "1.0.0"


def config_dir():
    base = os.environ.get("APPDATA") if os.name == "nt" else os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))
    d = Path(base or Path.home()) / "netconfig-app"
    d.mkdir(parents=True, exist_ok=True)
    return d


SETTINGS_FILE = config_dir() / "settings.json"

# ---------------------------------------------------------------- vendors, tasks, prompt building

VENDORS = {
    "cisco-ios":   {"label": "Cisco router / switch", "hint": "ISR, Catalyst, IOS / IOS-XE", "refs": ["cisco-ios"], "version": "show version"},
    "cisco-asa":   {"label": "Cisco ASA / Firepower", "hint": "ASA firewall, FTD", "refs": ["cisco-asa-ftd"], "version": "show version"},
    "cisco-nxos":  {"label": "Cisco Nexus", "hint": "NX-OS data-center switch", "refs": ["cisco-nxos"], "version": "show version"},
    "fortigate":   {"label": "FortiGate", "hint": "Fortinet firewall, FortiOS", "refs": ["fortigate"], "version": "get system status"},
    "paloalto":    {"label": "Palo Alto", "hint": "PA-series firewall, PAN-OS", "refs": ["paloalto"], "version": "show system info"},
    "juniper":     {"label": "Juniper", "hint": "SRX, MX, EX, Junos", "refs": ["juniper"], "version": "show version"},
    "mikrotik":    {"label": "MikroTik", "hint": "RouterOS routers, hAP, CCR", "refs": ["mikrotik"], "version": "/system resource print"},
    "checkpoint":  {"label": "Check Point", "hint": "Gaia gateways", "refs": ["checkpoint"], "version": "show version all"},
    "huawei":      {"label": "Huawei / H3C", "hint": "VRP routers & switches, USG", "refs": ["huawei"], "version": "display version"},
    "aruba":       {"label": "Aruba / HPE", "hint": "AOS-CX, ProCurve switches", "refs": ["aruba"], "version": "show version"},
    "arista":      {"label": "Arista", "hint": "EOS switches", "refs": ["arista"], "version": "show version"},
    "linux":       {"label": "Linux server firewall", "hint": "UFW, nftables, iptables", "refs": ["host-cloud"], "version": "cat /etc/os-release; nft --version"},
    "cloud":       {"label": "Cloud firewall", "hint": "AWS, Azure, GCP, Kubernetes", "refs": ["host-cloud"], "version": ""},
    "other":       {"label": "Other", "hint": "SonicWall, pfSense, VyOS, Sophos, UniFi", "refs": ["others"], "version": ""},
    "unknown":     {"label": "Not sure", "hint": "Paste the config and the app will try to tell", "refs": [], "version": ""},
}

TASKS = {
    "new":       {"label": "Set up something new", "refs": [],
                  "mode": "This is a NEW build or a lab (nothing existing to conflict with). Skip state collection."},
    "change":    {"label": "Change a device that is running", "refs": ["change-workflow"],
                  "mode": "This is a CHANGE TO A LIVE DEVICE. Follow the existing-device change workflow."},
    "fix":       {"label": "Fix a problem", "refs": ["change-workflow"],
                  "mode": "This is TROUBLESHOOTING. Follow the troubleshooting method; ask for the specific read-only outputs you need, and explain how to read them."},
    "review":    {"label": "Check my config for problems", "refs": ["audit-checklist", "sanitizing-configs"],
                  "mode": "This is a CONFIG REVIEW / SECURITY AUDIT. Use the audit checklist and a findings table."},
    "migrate":   {"label": "Move to another brand", "refs": ["migration-guide"],
                  "mode": "This is a CROSS-VENDOR MIGRATION. Follow the migration guide."},
    "question":  {"label": "Just ask a question", "refs": [],
                  "mode": "This is a QUESTION. Answer it directly and briefly; no change workflow unless asked."},
}

APP_PREAMBLE = """You are NetConfig Assistant, a careful senior network engineer helping someone through a desktop app.
The person may be NEW to networking. Follow the network-config skill below exactly (its workflow, safety
rules and output structure), and also:
- Use plain language. Define a technical term the first time you use it (a few words in brackets).
- Before each code block, say in one sentence what it does and where to type it (which device, which mode).
- Keep the skill's structure, with clear headings. Use markdown tables for checklists and acceptance tests.
- Code blocks must contain only commands to paste, with the right language tag (e.g. ```text).
- You cannot connect to devices; the person runs every command themselves. Never ask for passwords.
- Values shown as <REDACTED-n> were secrets removed by the app. Keep them as <REDACTED-n> in commands and
  tell the person to put their real value back in before pasting.
- If something essential for a safe change is missing (OS version for a live device, how they are connected),
  ask for it first in at most 3 short questions, and explain why each matters.
- Reply in the same language the person writes in.
The skill's reference files for this request are already included below: do not ask to read files.
"""


def read_skill():
    core = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", core, re.S)
    meta = m.group(1) if m else ""
    version = (re.search(r'version:\s*"?([^"\n]+)', meta) or [None, "?"])[1]
    body = core[m.end():] if m else core
    return body, version


SIGNATURES = [  # (vendor id, regex) used when the person picked "Not sure" and pasted a config
    ("fortigate", r"^config (system|firewall) |^\s+set \S+ |get system status"),
    ("paloalto", r"<config version=|set deviceconfig |set rulebase security"),
    ("juniper", r"^set (system|interfaces|security|protocols) |^\s*(system|interfaces) \{"),
    ("mikrotik", r"^/(ip|interface|system|routing) "),
    ("cisco-asa", r"^ASA Version|^access-list \S+ extended|^object network |nameif "),
    ("cisco-nxos", r"^feature |NX-OS|^vpc domain"),
    ("huawei", r"^sysname |^display |^ip vpn-instance|^#\s*$"),
    ("arista", r"Arista|^management api http-commands"),
    ("aruba", r"ArubaOS|AOS-CX|^vsx\b"),
    ("checkpoint", r"^set static-route |Gaia|^add host name "),
    ("linux", r"^table inet |^\*filter|^-A INPUT|ufw "),
    ("cisco-ios", r"^hostname |^interface (Gigabit|FastEthernet|Vlan|Loopback)|^ip route |^line vty"),
]


def guess_vendors(text):
    hits = []
    for vid, rx in SIGNATURES:
        if re.search(rx, text, re.M) and vid not in hits:
            hits.append(vid)
    return hits[:2]


def build_system_prompt(vendor_ids, task_id, ipv6=False, has_config=False):
    body, _ = read_skill()
    refs = []
    for v in vendor_ids:
        refs += VENDORS.get(v, {}).get("refs", [])
    task = TASKS.get(task_id, TASKS["question"])
    refs += task["refs"]
    if ipv6:
        refs.append("ipv6")
    if has_config and "sanitizing-configs" not in refs:
        refs.append("sanitizing-configs")
    seen, parts = set(), []
    for r in refs:
        f = SKILL_DIR / "references" / f"{r}.md"
        if r in seen or not f.is_file():
            continue
        seen.add(r)
        parts.append(f"\n\n=== reference: references/{r}.md ===\n" + f.read_text(encoding="utf-8"))
    mode = f"\n\nREQUEST TYPE: {task['mode']}\n"
    return APP_PREAMBLE + mode + "\n=== network-config skill: SKILL.md ===\n" + body + "".join(parts), sorted(seen)


# ---------------------------------------------------------------- settings & providers

PRESETS = {
    "llama-server": {"label": "llama.cpp server (local)", "kind": "openai", "base_url": "http://127.0.0.1:8080/v1", "needs_key": False},
    "ollama":       {"label": "Ollama (local)", "kind": "openai", "base_url": "http://127.0.0.1:11434/v1", "needs_key": False},
    "lmstudio":     {"label": "LM Studio (local)", "kind": "openai", "base_url": "http://127.0.0.1:1234/v1", "needs_key": False},
    "anthropic":    {"label": "Claude (Anthropic API)", "kind": "anthropic", "base_url": "https://api.anthropic.com/v1", "needs_key": True},
    "openai":       {"label": "OpenAI API", "kind": "openai", "base_url": "https://api.openai.com/v1", "needs_key": True},
    "custom":       {"label": "Other OpenAI-compatible server", "kind": "openai", "base_url": "", "needs_key": False},
}

DEFAULT_SETTINGS = {"preset": "llama-server", "base_url": PRESETS["llama-server"]["base_url"], "model": "",
                    "api_key": "", "temperature": 0.2, "max_tokens": 8192, "mask_public_ips": False}


def load_settings():
    s = dict(DEFAULT_SETTINGS)
    try:
        s.update(json.loads(SETTINGS_FILE.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        pass
    return s


def save_settings(new):
    s = load_settings()
    for k in DEFAULT_SETTINGS:
        if k in new:
            s[k] = new[k]
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(json.dumps(s, indent=2), encoding="utf-8")
    try:
        os.chmod(SETTINGS_FILE, 0o600)
    except OSError:
        pass
    return s


def public_settings(s):
    out = dict(s)
    out["api_key"] = ("•" * 8 + s["api_key"][-4:]) if s.get("api_key") else ""
    out["has_key"] = bool(s.get("api_key"))
    return out


def kind_of(s):
    return PRESETS.get(s.get("preset"), PRESETS["custom"])["kind"]


def _request(url, headers=None, body=None, timeout=20):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=dict({"Content-Type": "application/json"}, **(headers or {})),
                                 method="POST" if data else "GET")
    return urllib.request.urlopen(req, timeout=timeout)


class APIError(Exception):
    def __init__(self, code, detail):
        super().__init__(f"HTTP {code}: {detail}")
        self.code, self.detail = code, detail


def _post_adaptive(url, headers, body, timeout):
    """POST, and if the model rejects an optional parameter (newer models refuse `temperature`,
    OpenAI reasoning models want `max_completion_tokens`), drop or rename it and retry."""
    body = dict(body)
    for _ in range(4):
        try:
            return _request(url, headers, body, timeout=timeout)
        except urllib.error.HTTPError as e:
            detail = ""
            try:
                detail = e.read().decode("utf-8", "replace")
            except Exception:
                pass
            low = detail.lower()
            if e.code == 400 and "temperature" in low and "temperature" in body:
                body.pop("temperature")
                continue
            if e.code == 400 and "max_completion_tokens" in low and "max_tokens" in body:
                body["max_completion_tokens"] = body.pop("max_tokens")
                continue
            if e.code == 400 and "top_p" in low and "top_p" in body:
                body.pop("top_p")
                continue
            raise APIError(e.code, detail[:400])
    raise APIError(400, "the AI service rejected the request settings")


def auth_headers(s):
    if kind_of(s) == "anthropic":
        return {"x-api-key": s.get("api_key", ""), "anthropic-version": "2023-06-01"}
    return {"Authorization": f"Bearer {s['api_key']}"} if s.get("api_key") else {}


def list_models(s):
    base = s["base_url"].rstrip("/")
    with _request(f"{base}/models", auth_headers(s), timeout=8) as r:
        data = json.load(r)
    items = data.get("data", data.get("models", []))
    return sorted({m.get("id") or m.get("name") for m in items if isinstance(m, dict)} - {None})


def detect_local():
    found = []
    for key in ("llama-server", "ollama", "lmstudio"):
        try:
            models = list_models({"preset": key, "base_url": PRESETS[key]["base_url"], "api_key": ""})
            found.append({"preset": key, "label": PRESETS[key]["label"], "models": models})
        except Exception:
            pass
    return found


def stream_chat(s, system, messages, emit):
    """Call the model and emit ("delta"|"thinking", text). Returns when the stream ends."""
    base = s["base_url"].rstrip("/")
    if kind_of(s) == "anthropic":
        body = {"model": s["model"], "system": system, "messages": messages, "stream": True,
                "max_tokens": int(s.get("max_tokens") or 8192), "temperature": float(s.get("temperature", 0.2))}
        r = _post_adaptive(f"{base}/messages", auth_headers(s), body, timeout=300)
        for raw in r:
            line = raw.decode("utf-8", "replace").strip()
            if not line.startswith("data:"):
                continue
            ev = json.loads(line[5:].strip() or "{}")
            if ev.get("type") == "content_block_delta":
                d = ev.get("delta", {})
                if d.get("type") == "text_delta":
                    emit("delta", d.get("text", ""))
                elif d.get("type") == "thinking_delta":
                    emit("thinking", d.get("thinking", ""))
            elif ev.get("type") == "error":
                raise RuntimeError(ev.get("error", {}).get("message", "API error"))
        return
    body = {"model": s["model"] or "default", "stream": True, "temperature": float(s.get("temperature", 0.2)),
            "max_tokens": int(s.get("max_tokens") or 8192),
            "messages": [{"role": "system", "content": system}] + messages}
    r = _post_adaptive(f"{base}/chat/completions", auth_headers(s), body, timeout=600)
    for raw in r:
        line = raw.decode("utf-8", "replace").strip()
        if not line.startswith("data:"):
            continue
        payload = line[5:].strip()
        if payload == "[DONE]":
            break
        ev = json.loads(payload)
        if "error" in ev:
            raise RuntimeError(str(ev["error"]))
        for ch in ev.get("choices", []):
            d = ch.get("delta", {})
            if d.get("reasoning_content"):
                emit("thinking", d["reasoning_content"])
            if d.get("content"):
                emit("delta", d["content"])


# ---------------------------------------------------------------- HTTP server

class Handler(BaseHTTPRequestHandler):
    server_version = "NetConfigAssistant/" + APP_VERSION

    def log_message(self, fmt, *args):  # keep the console quiet
        pass

    def _local_only(self):
        host = (self.headers.get("Host") or "").split(":")[0]
        origin = self.headers.get("Origin")
        if host not in ("127.0.0.1", "localhost"):
            return False
        if origin and not re.match(r"^https?://(127\.0\.0\.1|localhost)(:\d+)?$", origin):
            return False
        return True

    def _json(self, obj, code=200):
        b = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(b)

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"{}") if n else {}

    def do_GET(self):
        if not self._local_only():
            return self._json({"error": "forbidden"}, 403)
        path = self.path.split("?")[0]
        if path == "/api/status":
            try:
                _, ver = read_skill()
                skill_ok = True
            except OSError:
                ver, skill_ok = None, False
            return self._json({"app_version": APP_VERSION, "skill_version": ver, "skill_ok": skill_ok,
                               "skill_dir": str(SKILL_DIR), "vendors": VENDORS,
                               "tasks": {k: {"label": v["label"]} for k, v in TASKS.items()},
                               "presets": PRESETS, "settings": public_settings(load_settings())})
        if path == "/api/detect":
            return self._json({"local": detect_local()})
        if path == "/":
            path = "/index.html"
        f = (STATIC / path.lstrip("/")).resolve()
        if STATIC not in f.parents or not f.is_file():
            return self._json({"error": "not found"}, 404)
        ctype = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8",
                 ".css": "text/css; charset=utf-8", ".svg": "image/svg+xml"}.get(f.suffix, "application/octet-stream")
        b = f.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:")
        self.end_headers()
        self.wfile.write(b)

    def do_POST(self):
        if not self._local_only():
            return self._json({"error": "forbidden"}, 403)
        try:
            body = self._body()
        except ValueError:
            return self._json({"error": "bad JSON"}, 400)
        if self.path == "/api/settings":
            s = dict(body)
            if s.get("api_key", "").startswith("•"):
                s.pop("api_key")  # unchanged masked key
            return self._json({"settings": public_settings(save_settings(s))})
        if self.path == "/api/models":
            s = load_settings()
            s.update({k: v for k, v in body.items() if k in ("preset", "base_url") or (k == "api_key" and v and not v.startswith("•"))})
            try:
                return self._json({"models": list_models(s)})
            except Exception as e:
                return self._json({"error": friendly_error(e, s)}, 502)
        if self.path == "/api/sanitize":
            clean, found = sanitize(body.get("text", ""), mask_public_ips=bool(body.get("mask_public_ips")))
            return self._json({"text": clean, "findings": found})
        if self.path == "/api/chat":
            return self._chat(body)
        return self._json({"error": "not found"}, 404)

    def _chat(self, body):
        s = load_settings()
        vendors = [v for v in body.get("vendors", []) if v in VENDORS]
        if (not vendors or vendors == ["unknown"]) and body.get("messages"):
            vendors = guess_vendors(body["messages"][0].get("content", "")) or vendors
        system, refs = build_system_prompt(vendors, body.get("task", "question"),
                                           ipv6=bool(body.get("ipv6")), has_config=bool(body.get("has_config")))
        messages = [{"role": m["role"], "content": m["content"]} for m in body.get("messages", [])
                    if m.get("role") in ("user", "assistant") and m.get("content")]
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        lock = threading.Lock()

        def emit(kind, text):
            with lock:
                self.wfile.write(f"data: {json.dumps({'type': kind, 'text': text})}\n\n".encode())
                self.wfile.flush()

        try:
            emit("meta", json.dumps({"refs": refs, "model": s.get("model"), "provider": PRESETS.get(s["preset"], {}).get("label")}))
            if not s.get("model"):
                raise RuntimeError("No model selected. Open Settings and choose a model.")
            stream_chat(s, system, messages, emit)
            emit("done", "")
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as e:
            try:
                emit("error", friendly_error(e, s))
            except OSError:
                pass


def friendly_error(e, s):
    if isinstance(e, APIError):
        msg = e.detail
        try:
            j = json.loads(e.detail)
            msg = (j.get("error") or {}).get("message") or j.get("message") or e.detail
        except (ValueError, AttributeError):
            pass
        if e.code in (401, 403):
            return f"The AI service refused the request ({e.code}). Check the API key in Settings. {msg}"
        if e.code == 404:
            return f"Not found at {s.get('base_url')} ({e.code}). Check the server address and model name. {msg}"
        if e.code == 429:
            return f"The AI service is busy or your usage limit was reached (429). Wait a moment and try again. {msg}"
        return f"The AI service returned an error ({e.code}): {msg}"
    if isinstance(e, urllib.error.HTTPError):
        detail = ""
        try:
            detail = e.read().decode("utf-8", "replace")[:300]
        except Exception:
            pass
        if e.code in (401, 403):
            return f"The AI service refused the request ({e.code}). Check the API key in Settings."
        if e.code == 404:
            return f"Not found at {s.get('base_url')} ({e.code}). Check the server address and model name. {detail}"
        return f"The AI service returned an error ({e.code}). {detail}"
    if isinstance(e, urllib.error.URLError):
        return (f"Can't reach the AI at {s.get('base_url')}. Is the model server running? "
                f"(For llama.cpp: start llama-server; for Ollama: open Ollama.) Details: {e.reason}")
    if isinstance(e, socket.timeout):
        return "The AI took too long to answer. Try again, or pick a smaller/faster model in Settings."
    return str(e)


def free_port(preferred=8765):
    for p in range(preferred, preferred + 20):
        with socket.socket() as sck:
            if sck.connect_ex(("127.0.0.1", p)) != 0:
                return p
    return 0


def main():
    if not (SKILL_DIR / "SKILL.md").is_file():
        print(f"Can't find the skill at {SKILL_DIR}.\nRun the app from the netconfig-skill folder, "
              "or set NETCONFIG_SKILL_DIR to the folder that contains SKILL.md.")
        sys.exit(1)
    port = int(os.environ.get("NETCONFIG_PORT") or free_port())
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = f"http://127.0.0.1:{port}/"
    _, ver = read_skill()
    print(f"NetConfig Assistant {APP_VERSION} (skill v{ver}) is running at {url}")
    print("Keep this window open while you use the app. Close it (or press Ctrl+C) to stop.")
    if "--no-browser" not in sys.argv:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
