"""Hide sensitive data in network configs before they are sent to an AI model.

Follows skills/network-config/references/sanitizing-configs.md: replace values (never delete
lines), give the same value the same placeholder every time, keep structure and syntax so the
config can still be diagnosed.

Three levels:
  * secrets (always): passwords, keys, SNMP communities, PSKs, private keys, API tokens
    -> <REDACTED-n>. Never shown again, not even in the answer.
  * public IP addresses (optional): mapped into documentation / benchmarking ranges, one /24 (IPv4)
    or /48 (IPv6) at a time, keeping the host part, so addresses that were in the same subnet stay
    in the same subnet and gateways, masks and NAT logic still make sense.
  * names (optional): hostnames, domain names, user names, descriptions/comments/aliases, SNMP
    location/contact, banners and e-mail addresses -> HOST-n, domainN.example, USER-n, DESC-n,
    LOCATION-n, CONTACT-n, BANNER-n, userN@example.com.

`state` carries the mappings between calls (initial config, follow-ups), so a value keeps its
placeholder for the whole conversation. IP and name placeholders can be turned back into the real
values on the user's own computer (see `restore_pairs`); secrets cannot.
"""
import ipaddress
import re

# ---------------------------------------------------------------------------------------- secrets
# (label, compiled regex). Group "v" is the secret value that gets replaced.
_RULES = [
    ("private key", re.compile(r"(?P<v>-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----)", re.S)),
    ("certificate", re.compile(r"(?P<v>-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----)", re.S)),
    # FortiGate: every ENC blob (passwords, PSKs, keys)
    ("FortiGate encrypted value", re.compile(r"\bENC\s+(?P<v>[A-Za-z0-9+/=]{8,})")),
    ("FortiGate secret", re.compile(r"\bset\s+(?:password|passwd|psksecret|secret|key|private-key|community|auth-pwd|priv-pwd|sslvpn-password)\s+(?!ENC\b)(?P<v>\"[^\"]+\"|\S+)", re.I)),
    # Cisco IOS / ASA / NX-OS
    ("Cisco type-7 password (reversible)", re.compile(r"\bpassword\s+7\s+(?P<v>[0-9A-Fa-f]{4,})")),
    ("Cisco secret hash", re.compile(r"\b(?:enable|username\s+\S+(?:\s+privilege\s+\d+)?)\s+secret\s+(?:[0-9]+\s+)?(?P<v>\S+)")),
    ("enable password", re.compile(r"\benable\s+password\s+(?:[0-9]+\s+)?(?:level\s+\d+\s+)?(?P<v>\S+)")),
    ("username password", re.compile(r"\busername\s+\S+(?:\s+privilege\s+\d+)?\s+password\s+(?:[0-9]+\s+)?(?P<v>\S+)")),
    ("line password", re.compile(r"^\s+password\s+(?:[0-9]+\s+)?(?P<v>\S+)", re.M)),
    ("SNMP community", re.compile(r"\bsnmp-server\s+community\s+(?P<v>\S+)")),
    ("pre-shared key", re.compile(r"\b(?:pre-shared-key|ikev[12]\s+(?:local|remote)-authentication\s+pre-shared-key)\s+(?:ascii-text\s+|hexadecimal\s+)?(?:[0-9]+\s+)?\"?(?P<v>[^\s\";]+)\"?", re.I)),
    ("ISAKMP key", re.compile(r"\bcrypto\s+isakmp\s+key\s+(?:[0-9]+\s+)?(?P<v>\S+)")),
    ("key-string", re.compile(r"\bkey-string\s+(?:[0-9]+\s+)?(?P<v>\S+)")),
    ("TACACS/RADIUS key", re.compile(r"\b(?:tacacs-server|radius-server)\s+(?:host\s+\S+\s+)?key\s+(?:[0-9]+\s+)?(?P<v>\S+)")),
    ("server key", re.compile(r"^\s+key\s+(?:[0-9]+\s+)?(?P<v>\S+)\s*$", re.M)),
    ("routing protocol key", re.compile(r"\b(?:message-digest-key\s+\d+\s+md5|authentication-key|neighbor\s+\S+\s+password)\s+(?:[0-9]+\s+)?(?:md5\s+|sha\S*\s+)?(?:[0-9]\s+)?(?P<v>\S+)")),
    ("NTP key", re.compile(r"\bntp\s+authentication-key\s+\d+\s+md5\s+(?P<v>\S+)")),
    # Juniper
    ("Juniper $9$ secret (reversible)", re.compile(r"\"?(?P<v>\$9\$[^\s\";<]+)\"?")),
    ("password hash", re.compile(r"\"?(?P<v>\$[156]\$[^\s\";<]+)\"?")),
    ("Juniper secret", re.compile(r"\b(?:encrypted-password|secret|ascii-text|community)\s+\"(?P<v>[^\"]+)\"")),
    # Palo Alto (XML)
    ("Palo Alto secret", re.compile(r"<(phash|key|pre-shared-key|private-key|password|community)>(?P<v>[^<]+)</\1>")),
    # MikroTik
    ("MikroTik secret", re.compile(r"\b(?:password|private-key|secret|psk|wpa2-pre-shared-key|wpa-pre-shared-key|passphrase)=(?P<v>\"[^\"]*\"|\S+)")),
    # Huawei
    ("Huawei cipher", re.compile(r"\b(?:cipher|irreversible-cipher)\s+(?P<v>\S+)")),
    ("Huawei community", re.compile(r"\bsnmp-agent\s+community\s+(?:read|write)\s+(?:cipher\s+)?(?P<v>\S+)")),
    ("shared key", re.compile(r"(?<![\w-])shared-key\s+(?:cipher\s+)?(?P<v>\S+)")),
    # Generic API keys / tokens
    ("API key or token", re.compile(r"(?P<v>\b(?:sk-[A-Za-z0-9_-]{16,}|ghp_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16})\b)")),
]

_PLACEHOLDER = re.compile(r"^<(REDACTED|PUBLIC-IP)-\d+>$|^<[A-Z-]+>$")

# ------------------------------------------------------------------------------------------ names
# (kind, regex). Group "v" is the identifying value. Quotes around it are kept.
_Q = r"(?:\"(?P<v>[^\"\n]+)\"|(?P<v2>[^\s;\"]+))"          # quoted value or one token
_QL = r"(?:\"(?P<v>[^\"\n]+)\"|(?P<v2>[^\n;]+?))\s*;?\s*$"   # quoted value or rest of line
_NAME_RULES = [
    # host names
    ("host", re.compile(r"^\s*(?:hostname|sysname|set\s+(?:system\s+)?host-?name|host-name|set\s+deviceconfig\s+system\s+hostname)\s+" + _Q, re.M | re.I)),
    ("host", re.compile(r"/system\s+identity\s+set\s+name=" + _Q)),
    ("host", re.compile(r"<hostname>(?P<v>[^<]+)</hostname>")),
    # domain names
    ("domain", re.compile(r"^\s*(?:ip\s+domain[- ]name|ip\s+domain\s+name|domain-name|domain\s+name|dns\s+domain-name|dns\s+domain|set\s+(?:system\s+)?domain-name|set\s+domain|set\s+deviceconfig\s+system\s+domain|set\s+domainname|domainname)\s+" + _Q, re.M | re.I)),
    ("domain", re.compile(r"<domain>(?P<v>[^<]+)</domain>")),
    # user names
    ("user", re.compile(r"^\s*(?:username|local-user|set\s+system\s+login\s+user|set\s+mgt-config\s+users|add\s+user)\s+" + _Q, re.M)),
    ("user", re.compile(r"^\s*user\s+(?P<v>[A-Za-z0-9_.@-]+)\s*\{", re.M)),
    ("user", re.compile(r"/user\s+add\b[^\n]*?\bname=" + _Q)),
    # descriptions, comments, aliases (FortiOS `set comments`, MikroTik `comment=`)
    ("desc", re.compile(r"^\s*(?:description|remark|set\s+description|set\s+comments?|set\s+alias)\s+" + _QL, re.M)),
    ("desc", re.compile(r"\baccess-list\s+\S+\s+remark\s+" + _QL, re.M)),
    ("desc", re.compile(r"[^\S\n]description\s+\"(?P<v>[^\"\n]+)\"")),
    ("desc", re.compile(r"\bcomment=" + _Q)),
    ("desc", re.compile(r"<description>(?P<v>[^<]+)</description>")),
    # SNMP location / contact
    ("location", re.compile(r"^\s*(?:snmp-server\s+location|snmp-agent\s+sys-info\s+location|set\s+snmp\s+location|location|set\s+location|snmp\s+location)\s+" + _QL, re.M)),
    ("location", re.compile(r"/snmp\s+set\b[^\n]*?\blocation=" + _Q)),
    ("contact", re.compile(r"^\s*(?:snmp-server\s+contact|snmp-agent\s+sys-info\s+contact|set\s+snmp\s+contact|contact|set\s+contact-info|snmp\s+contact)\s+" + _QL, re.M)),
    ("contact", re.compile(r"/snmp\s+set\b[^\n]*?\bcontact=" + _Q)),
    # login messages
    ("banner", re.compile(r"^\s*(?:set\s+system\s+login\s+message|message|set\s+deviceconfig\s+system\s+login-banner|header\s+(?:login|shell)\s+information)\s+\"(?P<v>[^\"]+)\"", re.M)),
]
# Cisco-style banners: banner motd ^C ... ^C (any delimiter)
_BANNER = re.compile(r"^(\s*banner\s+(?:motd|login|exec|incoming|asdm)\s+)(\^C|\S)(.*?)(\2)", re.M | re.S)
_EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
# FortiOS `config system admin` / `config user local`: `edit "name"` is a user name
_FORTI_USERS = re.compile(r"^(\s*config\s+(?:system\s+admin|user\s+local)\s*\n)(.*?)(^\s*end\s*$)", re.M | re.S)
_FORTI_EDIT = re.compile(r"^(\s*edit\s+)\"?(?P<v>[^\"\n]+?)\"?\s*$", re.M)

# values that are keywords or too generic to hide (hiding them would break commands)
_KEEP = {"admin", "root", "enable", "cisco", "guest", "operator", "readonly", "read-only", "none",
         "default", "local", "netadmin", "superuser", "super_admin", "manager", "monitor", "user",
         "users", "any", "all", "true", "false", "enable", "disable", "on", "off", "test", "lab",
         "router", "switch", "firewall", "fw", "rtr", "sw", "localhost", "localdomain", "example.com",
         "example.net", "example.org"}
# Descriptions made only of generic network words are kept ("WAN to ISP", "GUEST-WIFI", "uplink
# core-sw"): they help diagnosis and say nothing about who you are. Anything else is hidden.
_GENERIC_WORDS = set("""
wan lan dmz isp internet uplink downlink link trunk access core edge distribution dist mgmt management
oob guest guests staff users user voice data wifi wireless wlan ap aps printer printers camera cameras
cctv iot server servers srv web mail dns dhcp ntp vpn ipsec tunnel gre backup primary secondary main
standby ha sync heartbeat peer inside outside external internal public private to from for and the of
in out port ports vlan svi loopback lo mgmt0 firewall fw router rtr switch sw sw1 sw2 sw3 core1 core2
fw1 fw2 rtr1 rtr2 isp1 isp2 wan1 wan2 lan1 lan2 a b side left right new old temp test lab spare unused
reserved shutdown disabled not connected na n/a pc pcs office branch hq site dc cloud aws azure gcp
office365 o365 phones phone sip pbx voip video cluster member uplink1 uplink2 nat static default route
""".split())


def _generic(text):
    words = [w for w in re.split(r"[^A-Za-z0-9/]+", text.lower()) if w]
    return bool(words) and len(words) <= 6 and not any(ch.isdigit() for ch in text.replace("1", "").replace("2", "")) \
        and all(w in _GENERIC_WORDS for w in words)


# Well-known public resolvers / services: not sensitive, and useful for diagnosis
_KEEP_IPS = {"8.8.8.8", "8.8.4.4", "1.1.1.1", "1.0.0.1", "9.9.9.9", "149.112.112.112", "208.67.222.222",
             "208.67.220.220", "4.2.2.1", "4.2.2.2", "2001:4860:4860::8888", "2001:4860:4860::8844",
             "2606:4700:4700::1111", "2606:4700:4700::1001"}

_PREFIX = {"host": "HOST", "user": "USER", "desc": "DESC", "location": "LOCATION",
           "contact": "CONTACT", "banner": "BANNER"}

# --------------------------------------------------------------------------------------- IP pools
_V4_POOLS = ["198.51.100", "203.0.113", "192.0.2"] + [f"198.{18 + i // 256}.{i % 256}" for i in range(512)]


def new_state():
    return {"secrets": {}, "ips": {}, "nets4": {}, "nets6": {}, "names": {}, "count": {}}


def _norm_state(state):
    s = new_state()
    for k, v in (state or {}).items():
        if k in s and isinstance(v, dict):
            s[k] = dict(v)
    return s


def sanitize(text, mask_public_ips=False, hide_names=False, state=None):
    """Return (clean_text, findings, state).

    findings: [{"kind", "token", "label", "count", "original"}]; "original" is only filled for IPs
    and names (shown on the user's own screen), never for secrets.
    """
    st = _norm_state(state)
    counts = {}

    def count(token):
        counts[token] = counts.get(token, 0) + 1

    # --- secrets
    labels = {}

    def secret_token(value, label):
        if value not in st["secrets"]:
            st["secrets"][value] = f"<REDACTED-{len(st['secrets']) + 1}>"
        t = st["secrets"][value]
        labels[t] = label
        count(t)
        return t

    for label, rx in _RULES:
        def repl(m, label=label):
            v = m.group("v")
            if not v or _PLACEHOLDER.match(v) or v.lower() in {"0", "7", "5", "8", "9", "enc"}:
                return m.group(0)
            start, end = m.span("v")
            whole, off = m.group(0), m.start(0)
            return whole[: start - off] + secret_token(v, label) + whole[end - off:]
        text = rx.sub(repl, text)

    # --- names
    name_findings = {}

    def name_token(value, kind):
        value = value.strip()
        if kind == "desc" and _generic(value):
            return None
        if not value or _PLACEHOLDER.match(value) or value.lower() in _KEEP or re.fullmatch(
                r"(?:HOST|USER|DESC|LOCATION|CONTACT|BANNER)-\d+|domain\d+\.example|user\d+@example\.com", value):
            return None
        key = f"{kind}\0{value}"
        if key not in st["names"]:
            n = st["count"].get(kind, 0) + 1
            st["count"][kind] = n
            if kind == "domain":
                st["names"][key] = f"domain{n}.example"
            elif kind == "email":
                st["names"][key] = f"user{n}@example.com"
            else:
                st["names"][key] = f"{_PREFIX[kind]}-{n}"
        t = st["names"][key]
        name_findings[t] = (kind, value)
        count(t)
        return t

    if hide_names:
        def sub_group(m, kind):
            g = "v" if m.groupdict().get("v") is not None else "v2"
            v = m.group(g)
            if v is None:
                return m.group(0)
            t = name_token(v, kind)
            if not t:
                return m.group(0)
            start, end = m.span(g)
            whole, off = m.group(0), m.start(0)
            return whole[: start - off] + t + whole[end - off:]

        def banner_repl(m):
            body = m.group(3)
            if not body.strip():
                return m.group(0)
            t = name_token(body.strip(), "banner")
            return m.group(1) + m.group(2) + (f"\n{t}\n" if "\n" in body else t) + m.group(4) if t else m.group(0)

        text = _BANNER.sub(banner_repl, text)

        def forti_users(m):
            body = _FORTI_EDIT.sub(lambda e: (e.group(1) + '"' + (name_token(e.group("v"), "user") or e.group("v")) + '"'), m.group(2))
            return m.group(1) + body + m.group(3)

        text = _FORTI_USERS.sub(forti_users, text)
        for kind, rx in _NAME_RULES:
            text = rx.sub(lambda m, kind=kind: sub_group(m, kind), text)
        text = _EMAIL.sub(lambda m: name_token(m.group(0), "email") or m.group(0), text)

        # the same names elsewhere in the text (prompts, FQDNs, certificates, the user's own words)
        known = sorted(((k.split("\0", 1)[1], t, k.split("\0", 1)[0]) for k, t in st["names"].items()),
                       key=lambda x: -len(x[0]))
        for value, token, kind in known:
            if kind in ("desc", "banner", "location", "contact") or len(value) < 3:
                continue
            if kind == "domain":   # any FQDN ending in the domain: vpn.corp.example.eg -> vpn.domain1.example
                pat = re.compile(r"(?<![\w-])((?:[A-Za-z0-9-]+\.)*)" + re.escape(value) + r"(?![\w-])", re.I)
                text, n = pat.subn(lambda m: m.group(1) + token, text)
            else:
                pat = re.compile(r"(?<![\w.@-])" + re.escape(value) + r"(?![\w@-])")
                text, n = pat.subn(token, text)
            for _ in range(n):
                count(token)
            if n:
                name_findings[token] = (kind, value)

    # --- public IP addresses (prefix-preserving)
    ip_findings = {}
    if mask_public_ips:
        def v4_repl(m):
            s = m.group(0)
            try:
                ip = ipaddress.IPv4Address(s)
            except ValueError:
                return s
            if s in _KEEP_IPS or not ip.is_global or s.startswith(tuple(p + "." for p in _V4_POOLS[:3])) or s.startswith("198.18.") \
                    or s.startswith("198.19."):
                return s
            if s in st["ips"]:
                fake = st["ips"][s]
            else:
                net = s.rsplit(".", 1)[0]
                if net not in st["nets4"]:
                    used = set(st["nets4"].values())
                    st["nets4"][net] = next(p for p in _V4_POOLS if p not in used)
                fake = st["nets4"][net] + "." + s.rsplit(".", 1)[1]
                st["ips"][s] = fake
            ip_findings[fake] = s
            count(fake)
            return fake

        text = re.sub(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d]|\.\d)", v4_repl, text)

        def v6_repl(m):
            s = m.group(0)
            try:
                ip = ipaddress.IPv6Address(s)
            except ValueError:
                return s
            if ip.compressed in _KEEP_IPS or not ip.is_global or ip in ipaddress.IPv6Network("2001:db8::/32"):
                return s
            if s in st["ips"]:
                fake = st["ips"][s]
            else:
                packed = ip.packed
                net = packed[:6].hex()
                if net not in st["nets6"]:
                    st["nets6"][net] = len(st["nets6"]) + 1
                n = st["nets6"][net]
                fake_ip = ipaddress.IPv6Address(bytes.fromhex("20010db8") + n.to_bytes(2, "big") + packed[6:])
                fake = fake_ip.compressed
                st["ips"][s] = fake
            ip_findings[fake] = s
            count(fake)
            return fake

        text = re.sub(r"(?<![\w:.])(?=[0-9A-Fa-f:]*:[0-9A-Fa-f]*:)[0-9A-Fa-f:]{2,39}(?![\w:])", v6_repl, text)

    findings = [{"kind": "secret", "token": t, "label": labels[t], "count": counts.get(t, 0), "original": None}
                for t in labels]
    findings += [{"kind": kind, "token": t, "label": kind, "count": counts.get(t, 0), "original": v}
                 for t, (kind, v) in name_findings.items()]
    findings += [{"kind": "ip", "token": t, "label": "public IP", "count": counts.get(t, 0), "original": v}
                 for t, v in ip_findings.items()]
    return text, findings, st


def restore_pairs(state):
    """[(placeholder, original)] for names and IPs, longest placeholder first. Secrets are excluded."""
    st = _norm_state(state)
    pairs = [(t, k.split("\0", 1)[1]) for k, t in st["names"].items()]
    pairs += [(fake, real) for real, fake in st["ips"].items()]
    return sorted(pairs, key=lambda p: -len(p[0]))


if __name__ == "__main__":
    import sys
    clean, found, _ = sanitize(sys.stdin.read(), mask_public_ips="--ips" in sys.argv, hide_names="--names" in sys.argv)
    print(clean)
    for f in found:
        extra = f" (was {f['original']})" if f["original"] else ""
        print(f"# {f['token']}: {f['label']} x{f['count']}{extra}", file=sys.stderr)
