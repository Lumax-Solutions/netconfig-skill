# Contributing

Corrections from people who run this gear every day are the most valuable contribution.

## Ground rules

1. **Cite a source.** Every correction or new command needs an official vendor doc, release note
   or KB link, or device output from a stated OS version. Put the link in the PR description.
2. **Label versions.** If behaviour differs by release, say which versions each form applies to
   (e.g. "7.4.1+ … / 7.4.0 and older …").
3. **Paste-safe examples.** Command blocks must paste cleanly: no trailing `!`/`#` comments on
   command lines, placeholders as `<PSK>` / `<PASSWORD>`, example IPs from RFC 5737
   (`192.0.2.0/24`, `198.51.100.0/24`, `203.0.113.0/24`) and RFC 1918.
4. **Keep the core small.** Vendor syntax goes in `skills/network-config/references/<platform>.md`.
   `SKILL.md` only holds rules that apply to every platform. Adding a platform = new reference
   file + one row in the routing table in `SKILL.md`.
5. **Safety first.** Changes that touch remote management must keep the pre-check → backup →
   change → verify → rollback structure and an automatic rollback where the platform has one.

## Before opening a PR

```bash
python scripts/validate.py          # structure, links, paste-safety checks
python scripts/build_agents_md.py   # regenerate dist/AGENTS.md (CI fails if it's stale)
```

Update `CHANGELOG.md` and, for anything substantial, add or update a test case in
`skills/network-config/evals/` (see the README section on evaluations).

## Not accepted

Content for bypassing authentication on devices you don't administer, cracking other people's
device passwords, covert exfiltration, or anything else that helps attack networks.
