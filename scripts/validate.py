#!/usr/bin/env python3
"""Validate the network-config skill.

Checks:
  - SKILL.md has YAML frontmatter with `name` and `description`, and only the top-level keys the
    Agent Skills spec allows (client-specific fields such as Hermes' go under `metadata`)
  - metadata.version matches .claude-plugin/plugin.json
  - name is kebab-case, <= 64 chars, matches the folder name
  - description is <= 1024 chars and has no angle brackets
  - every `references/*.md` path mentioned in SKILL.md exists, and every reference file is linked
  - code fences are balanced in every markdown file
  - no trailing `!`/`#` comments on IOS / FortiOS command lines inside code blocks
  - no comment-only `#` lines in device paste blocks, and no other `commit …` (plain, `and-quit`, `comment`, `synchronize`) in the same block as `commit confirmed`
  - each eval case has prompt.md, case.yaml and at least one grader

Exit code 0 = OK, 1 = problems found.
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "network-config"
errors: list[str] = []


def err(msg: str) -> None:
    errors.append(msg)


def parse_frontmatter(text: str) -> dict:
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        err("SKILL.md: missing YAML frontmatter")
        return {}
    data = {}
    for line in m.group(1).splitlines():
        if re.match(r"^[a-z_-]+:", line):
            key, _, val = line.partition(":")
            data[key.strip()] = val.strip().strip('"')
    return data


skill_md = (SKILL / "SKILL.md").read_text(encoding="utf-8")
fm = parse_frontmatter(skill_md)
name = fm.get("name", "")
desc = fm.get("description", "")
if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name) or len(name) > 64:
    err(f"SKILL.md: invalid name {name!r}")
if name != SKILL.name:
    err(f"SKILL.md: name {name!r} must match folder {SKILL.name!r}")
if not desc:
    err("SKILL.md: missing description")
if len(desc) > 1024:
    err(f"SKILL.md: description is {len(desc)} chars (max 1024)")
if "<" in desc or ">" in desc:
    err("SKILL.md: description must not contain angle brackets")
# Agent Skills spec (agentskills.io, skills-ref validator): only these top-level keys are allowed.
SPEC_KEYS = {"name", "description", "license", "allowed-tools", "metadata", "compatibility"}
extra = sorted(set(fm) - SPEC_KEYS)
if extra:
    err(f"SKILL.md: top-level frontmatter keys {extra} are not allowed by the Agent Skills spec "
        "(validators reject them); put client-specific fields under `metadata:`")
fm_block = re.match(r"^---\n(.*?)\n---\n", skill_md, re.S).group(1)
skill_version = (re.search(r'(?m)^  version:\s*"?([^"\n]+)"?', fm_block) or [None, ""])[1]
plugin = ROOT / ".claude-plugin" / "plugin.json"
if plugin.is_file():
    import json
    pv = json.loads(plugin.read_text(encoding="utf-8")).get("version", "")
    if pv != skill_version:
        err(f"version mismatch: SKILL.md metadata.version {skill_version!r} vs plugin.json {pv!r}")
if not re.search(r"(?m)^  hermes:\n    category: networking$", fm_block):
    err("SKILL.md: metadata.hermes.category should be 'networking' (matches the installers)")

linked = set(re.findall(r"references/([a-z0-9-]+\.md)", skill_md))
present = {p.name for p in (SKILL / "references").glob("*.md")}
for f in sorted(linked - present):
    err(f"SKILL.md links missing file references/{f}")
for f in sorted(present - linked):
    err(f"references/{f} is not linked from SKILL.md")

TRAILING = re.compile(r"^\s*(?!!)(?!#)\S.*\s(!|#)\s+\S")
for md in [SKILL / "SKILL.md", *sorted((SKILL / "references").glob("*.md"))]:
    text = md.read_text(encoding="utf-8")
    fences = re.findall(r"(?m)^```", text)
    if len(fences) % 2:
        err(f"{md.relative_to(ROOT)}: unbalanced code fences")
    # trailing-comment check only for IOS-like / FortiOS files (shell files may use # comments)
    if md.name in {"cisco-ios.md", "cisco-nxos.md", "cisco-asa-ftd.md", "fortigate.md", "huawei.md", "aruba.md", "arista.md"}:
        in_code = False
        for n, line in enumerate(text.splitlines(), 1):
            if line.startswith("```"):
                in_code = not in_code
                continue
            if in_code and TRAILING.match(line) and "'" not in line and '"' not in line:
                err(f"{md.relative_to(ROOT)}:{n}: trailing comment on a command line: {line.strip()}")

# Paste blocks: no comment-only "# ..." lines in device CLI blocks (PAN-OS / Junos configure mode and
# others reject or misparse them; put headings outside the block), and never "commit" in the same block
# as "commit confirmed" (that confirms instantly and defeats the automatic rollback).
SHELL_LANGS = {"bash", "sh", "shell", "console", "powershell", "ps1", "yaml", "json", "python", "nft"}
for md in [SKILL / "SKILL.md", *sorted((SKILL / "references").glob("*.md"))]:
    in_code, lang, block = False, "", []
    for n, line in enumerate(md.read_text(encoding="utf-8").splitlines(), 1):
        if line.startswith("```"):
            in_code = not in_code
            lang, block = line[3:].strip().lower(), []
            continue
        if not in_code:
            continue
        stripped = line.strip()
        if (stripped.startswith("#") and md.name != "host-cloud.md" and lang not in SHELL_LANGS):
            err(f"{md.relative_to(ROOT)}:{n}: comment line inside a paste block (move it outside): {stripped}")
        # any commit (plain, and-quit, comment ..., synchronize ...) except check/confirmed
        is_confirming_commit = (re.match(r"commit(\s|$)", stripped)
                                and not re.match(r"commit\s+(check|confirmed)\b", stripped))
        if is_confirming_commit and any(b.startswith("commit confirmed") for b in block):
            err(f"{md.relative_to(ROOT)}:{n}: '{stripped}' in the same paste block as 'commit confirmed' "
                "(confirms immediately; split it so the user tests first)")
        block.append(stripped)

evals = SKILL / "evals"
if evals.is_dir():
    for case in sorted(p for p in evals.iterdir() if p.is_dir()):
        for req in ("prompt.md", "case.yaml"):
            if not (case / req).is_file():
                err(f"evals/{case.name}: missing {req}")
        if not list((case / "graders").glob("*.md")):
            err(f"evals/{case.name}: no graders")

# SOURCES.md: well-formed rows and freshness (warn when a source is over 12 months old)
import datetime
sources = ROOT / "SOURCES.md"
stats = {}
if sources.is_file():
    today = datetime.date.today()
    for n, line in enumerate(sources.read_text(encoding="utf-8").splitlines(), 1):
        if not re.match(r"\|\s*[A-Z]\d+\s*\|", line):
            continue
        cells = [c.strip() for c in re.split(r"(?<!\\)\|", line.strip().strip("|"))]
        if len(cells) != 7:
            err(f"SOURCES.md:{n}: expected 7 columns, found {len(cells)}")
            continue
        status = cells[3].split()[0] if cells[3] else ""
        if status not in ("VERIFIED", "CORRECTED", "UNVERIFIED"):
            err(f"SOURCES.md:{n}: unknown status {cells[3]!r}")
        stats[status] = stats.get(status, 0) + 1
        try:
            checked = datetime.date.fromisoformat(cells[6])
        except ValueError:
            err(f"SOURCES.md:{n}: last-checked date {cells[6]!r} is not YYYY-MM-DD")
            continue
        if (today - checked).days > 365:
            print(f"::warning file=SOURCES.md,line={n}::{cells[0]} last checked {checked} (over 12 months): re-verify the source")
else:
    err("SOURCES.md is missing")

if errors:
    print("Validation FAILED:")
    for e in errors:
        print("  -", e)
    sys.exit(1)
print(f"OK: {name} — {len(present)} reference files, description {len(desc)} chars, "
      f"sources: " + ", ".join(f"{v} {k.lower()}" for k, v in sorted(stats.items())))
