# Codex tests for network-config

A reusable public test kit preserving three original tests: the v1.2.0 paired answer-quality smoke test, its v1.2.1 retest, and a v1.2.1 automatic-activation test. This kit contains prompts, original manual grades, sanitized activation evidence and final answer samples. It does not install or modify a skill, connect to devices, or push to GitHub.

## Requirements and provenance

- Python 3.10+; standard library only. Packaging validation used Python 3.14.4.
- Codex CLI with `exec`, `--ignore-user-config`, `--ephemeral`, `--json`, read-only sandbox, and the `skip_host_skill_discovery`, `shell_tool`, `skill_search` switches. The local CLI used for these tests reports **codex-cli 0.167.0-alpha.3.2** at packaging time. Its version was not recorded separately during the original runs, so exact historical binary identity cannot be independently confirmed. These experimental switches/event shapes may change.
- Existing authorized Codex login and model access. Real runs consume model usage; dry runs do not launch Codex or require authentication. Credentials are neither read nor copied by these Python scripts.
- A separate checkout or installed copy of the matching skill version. No installed skill files are included here. For activation, the skill must already be installed in a normal location discovered by Codex; `--skill-dir` verifies/fingerprints it but does not inject or register it.
- Run from a trusted local copy. Depending on local sandbox permissions, the CLI may need permission to access its own state/auth directory. The scripts never bypass sandboxing or approval policy.

The original exact model identifier was not pinned/captured. Both conditions used the same default CLI settings, but deterministic historical reproduction is impossible. An optional `--model MODEL_ID` pins future runs and is a methodological difference to record.

## What the tests measure

**Answer quality:** two new sessions receive the same three cases. Discovery is disabled for both; the treatment receives the core plus four references directly in its prompt. This is a supplied-content comparison, not automatic activation. Score answers manually against the unchanged 20-item `rubric.json` (8 + 8 + 4), and separately review factual correctness. `RESULTS.md` preserves both historical pairs and the `match-vip` regression.

**Activation:** twelve fresh sessions receive natural requests with discovery enabled: eight intended matches and four controls. Successful reads of the installed core count as activation. No contents or skill name are injected. The harness extracts relative read evidence in memory; the summarizer produces an observed-versus-expected table. This tests CLI discovery only.

## Configuration

Both runners accept:

| Argument | Environment fallback | Default |
|---|---|---|
| `--skill-dir` | `NETWORK_CONFIG_SKILL_DIR` | `<CODEX_HOME>/skills/network-config`, or the normal home `.codex/skills/network-config` |
| `--output-dir` | `CODEX_TEST_OUTPUT_DIR` | `answer-quality-results` or `activation-results` under the invoking directory |
| `--codex` | `CODEX_EXECUTABLE` | `codex` on PATH |
| `--model` | none | CLI default, matching the original method |
| `--workers` | none | 2 for answer quality; 3 for activation |
| `--timeout` | none | 600 seconds per answer session; 480 per activation session |
| `--dry-run` | none | Off; validates inputs and renders prompts without model calls or output writes |

All paths are resolved at runtime. Use a fresh output directory for each test. No executable/path value is stored in JSON results. The selected skill paths in manifests are relative.

## Exact repeat commands

Run the following from the repository root, with this folder at `tests/codex/`. `python` may be `python3` on your OS; `--codex codex` may be replaced with your executable path.

Prepare separate, read-only version sources (does not alter the installed skill):

```sh
git clone --branch v1.2.0 --depth 1 https://github.com/Lumax-Solutions/netconfig-skill.git test-sources/v1.2.0
git clone --branch v1.2.1 --depth 1 https://github.com/Lumax-Solutions/netconfig-skill.git test-sources/v1.2.1
```

Repeat the v1.2.0 answer-quality test:

```sh
python tests/codex/answer-quality/run.py --skill-dir test-sources/v1.2.0/skills/network-config --output-dir test-runs/answer-v1.2.0 --codex codex
```

Repeat the v1.2.1 answer-quality test:

```sh
python tests/codex/answer-quality/run.py --skill-dir test-sources/v1.2.1/skills/network-config --output-dir test-runs/answer-v1.2.1 --codex codex
```

Repeat the v1.2.1 activation test, with v1.2.1 already installed in Codex's normal discovery location:

```sh
python tests/codex/activation/run.py --output-dir test-runs/activation-v1.2.1 --codex codex
```

If the installed copy is at a different discoverable location, pass `--skill-dir PATH_TO_INSTALLED_SKILL`. Merely pointing this argument at an uninstalled checkout does not make it discoverable. Confirm the installed metadata says 1.2.1 before comparing the historical activation result.

Regenerate a summary from a new run or from packaged evidence:

```sh
python tests/codex/activation/summarize.py --input test-runs/activation-v1.2.1/activation-evidence.json --output-dir test-runs/activation-v1.2.1
python tests/codex/activation/summarize.py --input tests/codex/activation/activation-results.json --output-dir test-runs/packaged-activation-summary
```

Non-model validation (add `--dry-run` to either answer-quality command above):

```sh
python -m py_compile tests/codex/answer-quality/run.py tests/codex/activation/run.py tests/codex/activation/summarize.py
python tests/codex/answer-quality/run.py --skill-dir test-sources/v1.2.1/skills/network-config --dry-run
python tests/codex/activation/run.py --dry-run
```

## Reading new results

- Answer quality produces `baseline.md`, `with-skill.md`, exact rendered prompts, relative SHA-256 manifest, unchanged cases/rubric, and sanitized per-arm metadata. Review manually; no automatic grader or fabricated score is supplied. A zero process return code plus `complete: true` is required before grading.
- Activation produces twelve answer files, `activation-evidence.json`, `activation-results.json`, `SUMMARY.md`, and a relative core hash manifest. `loaded: true` means a successful observed core read. `false` means a completed session with no recognized successful read. `null` means incomplete/unobserved; do not count it as a control success or miss. Preserve evidence if the CLI event schema changes.
- Neither runner saves raw JSONL events or stderr. Process failures produce a nonzero exit and sanitized status rather than potentially private raw diagnostics. Review any newly generated final answers before sharing; a model may still write local information into answer text.
- The activation evidence parser intentionally targets observed shell-based reads in the tested CLI event format, not every possible future file-reading tool.

## Preservation, privacy and portability changes

- `answer-quality/cases.txt`, `answer-quality/rubric.json` and `activation/cases.json` are byte-for-byte copies of the originals. The original synthetic `BRANCH` device label, documentation IPs and redacted credential marker remain because changing them would change the test inputs; these are not actual machine identities or secrets.
- The sample folder contains **only 16 final answer files**: two pairs in versioned directories plus twelve activation answers. No raw prompts with skill contents, skill source, staged releases, backups, stderr, JSONL logs, credentials or account/session/event IDs are included.
- Activation evidence retains case names, expectations, observed booleans, exit codes and character counts. Raw commands/home paths and local item IDs were replaced by skill-relative file paths; the misleading original `bytes` count was renamed `output_characters`. Unrelated command strings were omitted.
- Prompt templates contain only `{{CASES}}` and `{{SKILL_MATERIAL}}`. The harness constructs the same material header, reference order and separators as before, from the caller's skill checkout. No installed skill contents are shipped.
- Arguments/environment defaults replace all hard-coded user, executable, output and working-directory paths. Main guards prevent model execution on import. Events are parsed in memory, not written. Errors/timeouts return a failure status. Activation distinguishes unknown from negative observations. These are harness/privacy changes; test wording and expected outcomes did not change.
- Two versioned relative-path SHA-256 manifests preserve supplied-file provenance. Raw evidence is not present, so public readers cannot independently reparse the original sessions; the sanitized evidence and final samples are the retained record.
- No installed skill was changed and no model was called during packaging. Syntax, dry-run, prompt-equivalence, evidence-parser and privacy checks are performed locally.

## Historical results and limits

Answer-quality compliance: v1.2.0 19/20 vs 20/20; v1.2.1 18/20 vs 20/20. The v1.2.0 skill answer contained a factual error despite its checklist score. v1.2.1 passed that targeted regression. Activation: 8/8 intended matches, 0/4 false positives. See each `RESULTS.md` for evidence and limitations. These are small, unblinded, single-generation smoke tests, not proof of operational safety or a statistically reliable performance gain.
