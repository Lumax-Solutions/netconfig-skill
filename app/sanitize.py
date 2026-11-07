"""Remove secrets from pasted network configs before they are sent to an AI model.

Follows skills/network-config/references/sanitizing-configs.md: replace values (never delete
lines), keep the same token for the same secret, keep structure and names. Public IPv4 addresses
can optionally be mapped to documentation ranges, consistently.
"""
import ipaddress
import re

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
    ("routing protocol key", re.compile(r"\b(?:message-digest-key\s+\d+\s+md5|authentication-key|neighbor\s+\S+\s+password)\s+(?:[0-9]+\s+)?(?P<v>\S+)")),
    ("NTP key", re.compile(r"\bntp\s+authentication-key\s+\d+\s+md5\s+(?P<v>\S+)")),
    # Juniper
    ("Juniper $9$ secret (reversible)", re.compile(r"\"?(?P<v>\$9\$[^\s\";]+)\"?")),
    ("password hash", re.compile(r"\"?(?P<v>\$[156]\$[^\s\";]+)\"?")),
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


def sanitize(text, mask_public_ips=False):
    """Return (clean_text, findings). findings = list of {"label", "token", "count"}."""
    tokens = {}   # secret value -> token
    labels = {}   # token -> label
    counts = {}

    def token_for(value, label):
        if value not in tokens:
            tokens[value] = f"<REDACTED-{len(tokens) + 1}>"
            labels[tokens[value]] = label
        t = tokens[value]
        counts[t] = counts.get(t, 0) + 1
        return t

    for label, rx in _RULES:
        def repl(m, label=label):
            v = m.group("v")
            if not v or _PLACEHOLDER.match(v) or v.lower() in {"0", "7", "5", "8", "9", "enc"}:
                return m.group(0)
            start, end = m.span("v")
            whole = m.group(0)
            off = m.start(0)
            return whole[: start - off] + token_for(v, label) + whole[end - off:]
        text = rx.sub(repl, text)

    if mask_public_ips:
        mapping = {}
        doc_pool = [f"203.0.113.{i}" for i in range(1, 255)] + [f"198.51.100.{i}" for i in range(1, 255)]

        def ip_repl(m):
            s = m.group(0)
            try:
                ip = ipaddress.ip_address(s)
            except ValueError:
                return s
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved \
                    or ip.is_unspecified or s.startswith(("203.0.113.", "198.51.100.", "192.0.2.")):
                return s
            if s not in mapping:
                mapping[s] = doc_pool[len(mapping) % len(doc_pool)]
                labels[f"{s} -> {mapping[s]}"] = "public IP (mapped)"
                counts[f"{s} -> {mapping[s]}"] = 0
            counts[f"{s} -> {mapping[s]}"] += 1
            return mapping[s]
        # avoid touching masks like 255.255.255.0 and wildcard 0.0.0.255 (both is_reserved/private-ish handled above)
        text = re.sub(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])", ip_repl, text)

    findings = [{"token": t if t.startswith("<") else t.split(" -> ")[1], "label": labels[t], "count": counts[t],
                 "original_hint": None if t.startswith("<") else t.split(" -> ")[0]}
                for t in labels]
    return text, findings


if __name__ == "__main__":
    import sys
    clean, found = sanitize(sys.stdin.read(), mask_public_ips="--ips" in sys.argv)
    print(clean)
    for f in found:
        print(f"# {f['token']}: {f['label']} x{f['count']}", file=sys.stderr)
