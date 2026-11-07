# Sanitizing configs before sharing

Part of the `network-config` skill. Read `../SKILL.md` first for the workflow and safety rules.

Use this when the user is about to paste a config or output, or already pasted one containing secrets.

## What to do when a config with secrets is pasted

- Don't repeat secrets back in your answer; refer to them as `<redacted>` or by their line.
- Tell the user once, briefly, which secrets were exposed and which must be **rotated**, not just
  redacted: anything **reversible** — Cisco `password 7`, Juniper `$9$`, plain-text keys/PSKs,
  SNMP communities — is as good as plain text. Hashed secrets (Cisco `secret 8/9`, Junos `$6$`)
  are lower risk but still worth removing before sharing publicly.
- Keep working on the task; don't refuse because secrets were present.

## How to redact (guidance to give the user)

Goal: remove secrets and identifying details **while keeping every relationship the diagnosis
depends on** — object names, interface names, which rule references which object, subnet sizes,
and which addresses are the same as each other.

1. **Replace, don't delete.** Keep the line, swap the value: `pre-shared-key <PSK-1>`. Deleting
   lines hides structure the diagnosis needs.
2. **Be consistent.** The same secret or address gets the same token everywhere
   (`<PSK-1>`, `PUBLIC-IP-1`), so matching values still match.
3. **Keep subnet sizes and RFC 1918 ranges.** Private addresses usually need no redaction. For
   public IPs, map each to a documentation address (`203.0.113.x`, `198.51.100.x`) and keep the
   prefix length.
4. **Keep names unless they are sensitive.** Hostnames, usernames, customer or site names can
   become `SITE-A`, `USER-1` — consistently.

## Where secrets hide, per vendor

| Vendor | Look for |
|---|---|
| Cisco IOS/NX-OS | `enable secret`, `enable password`, `username ... secret/password`, `password 7 ...`, `key-string`, `pre-shared-key`, `crypto isakmp key`, `snmp-server community`, `tacacs-server key` / `key` under `tacacs server`, `radius-server key`, `ntp authentication-key`, `ip ospf message-digest-key`, BGP `neighbor ... password`, `crypto pki certificate` blocks |
| Cisco ASA | `enable password`, `username ... password`, `ikev1/ikev2 pre-shared-key`, `snmp-server host ... community`, `aaa-server ... key`, certificates and `crypto ca` blocks |
| FortiGate | Every `ENC ...` value (`set password ENC`, `set psksecret ENC`, `set passwd ENC`), `set community`, private keys under `config vpn certificate local`, `set private-key` |
| Palo Alto | `<phash>`, `<key>`, `pre-shared-key`, `<private-key>`, API keys, SNMP `community` |
| Juniper Junos | `encrypted-password`, `$9$...` (reversible), `authentication-key`, `pre-shared-key`, `secret`, `community`, `load-key-file` content |
| MikroTik | `/export` hides most secrets by default; `/export show-sensitive` includes them — share the plain `/export`. Watch `/interface wireguard` private keys and `/ppp secret` if shown |
| Huawei | `cipher` / `irreversible-cipher` values, `pre-shared-key`, `snmp-agent community`, `radius-server shared-key` |
| Linux | Private keys, `.env` files, cloud credentials in scripts; nft/iptables rules are usually safe |
| Cloud | Access keys, secrets in Terraform state or user-data |

## Safe ways to get configs

- Cisco: `show running-config` masks some secrets by type but not `password 7` — redact anyway.
- FortiGate: `show` output contains `ENC` blobs; they are encrypted but tied to the device key —
  still remove them before sharing publicly.
- MikroTik: plain `/export` (without `show-sensitive`).
- Junos: `show configuration | display set` then redact; or share only the hierarchy needed
  (`show configuration security policies`).
- Share only the sections the question needs (the relevant interfaces, policies, NAT, routes).
