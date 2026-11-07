#!/usr/bin/env python3
"""Fresh-session skill-discovery test; no injected skill contents or paths."""
import argparse
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
from summarize import summarize, write_results

HERE = Path(__file__).resolve().parent
SUFFIX = '\n\nPlease advise only. Do not connect to devices, execute configuration changes, or modify files.'


def evidence_from_events(text):
    reads, complete = [], False
    for line in text.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if event.get('type') == 'turn.completed':
            complete = True
        item = event.get('item', {})
        if event.get('type') != 'item.completed' or item.get('type') != 'command_execution':
            continue
        # Normalize escaped Windows separators; retain only paths relative to the skill root.
        command = re.sub(r'\\+', '/', item.get('command', ''))
        paths = sorted(set(re.findall(r'network-config/((?:references/)?[A-Za-z0-9_-]+\.md)', command)))
        for path in paths:
            reads.append({'path': path, 'exit_code': item.get('exit_code'),
                          'output_characters': len(item.get('aggregated_output', ''))})
    return complete, reads


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    default_skill = Path(os.environ.get('CODEX_HOME', Path.home() / '.codex')) / 'skills' / 'network-config'
    parser.add_argument('--skill-dir', type=Path, default=os.environ.get('NETWORK_CONFIG_SKILL_DIR', default_skill),
                        help='Preflight/fingerprint only: the skill must already be in a discoverable installed location.')
    parser.add_argument('--output-dir', type=Path, default=os.environ.get('CODEX_TEST_OUTPUT_DIR', 'activation-results'))
    parser.add_argument('--codex', default=os.environ.get('CODEX_EXECUTABLE', 'codex'))
    parser.add_argument('--model', default=None)
    parser.add_argument('--workers', type=int, default=3)
    parser.add_argument('--timeout', type=int, default=480)
    parser.add_argument('--dry-run', action='store_true', help='Validate cases and installed core only; never launch Codex or write outputs.')
    args = parser.parse_args()
    if args.workers < 1 or args.timeout < 1:
        parser.error('workers and timeout must be positive')
    try:
        cases = json.loads((HERE / 'cases.json').read_text(encoding='utf-8'))
        if len({x[0] for x in cases}) != len(cases) or any(not re.fullmatch(r'[a-z0-9_]+', x[0]) for x in cases):
            raise ValueError('Case names must be unique safe directory names')
        digest = hashlib.sha256((args.skill_dir.expanduser() / 'SKILL.md').read_bytes()).hexdigest()
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    if args.dry_run:
        print(json.dumps({'dry_run': True, 'cases': len(cases), 'should_load': sum(x[1] for x in cases),
                          'controls': sum(not x[1] for x in cases), 'core_sha256': digest}))
        return
    codex = shutil.which(args.codex)
    if codex is None:
        parser.error('Codex executable not found; pass --codex or set CODEX_EXECUTABLE')
    output = args.output_dir.expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    (output / 'skill-manifest.json').write_text(json.dumps({'SKILL.md': digest}, indent=2), encoding='utf-8')

    def run(case):
        name, expected, prompt = case
        work = output / 'sessions' / name
        work.mkdir(parents=True, exist_ok=True)
        if any(work.iterdir()):
            raise ValueError('Session directory is not empty; use a fresh output directory')
        command = [codex, 'exec', '--ignore-user-config', '--ephemeral', '--skip-git-repo-check',
                   '-s', 'read-only', '--disable', 'skip_host_skill_discovery', '-c', 'web_search="disabled"',
                   '-C', str(work), '--json', '-o', str(output / (name + '.md'))]
        if args.model:
            command += ['--model', args.model]
        command += ['-']
        start = time.monotonic()
        result = {'case': name, 'expected': expected, 'complete': False, 'requested_model': args.model,
                  'network_config_reads': []}
        try:
            proc = subprocess.run(command, input=prompt + SUFFIX, capture_output=True, encoding='utf-8',
                                  errors='replace', timeout=args.timeout)
            result['exit_code'] = proc.returncode
            result['complete'], result['network_config_reads'] = evidence_from_events(proc.stdout)
        except subprocess.TimeoutExpired:
            result['timeout'] = True
        except OSError:
            result['launch_failed'] = True
        result['seconds'] = round(time.monotonic() - start, 1)
        print(json.dumps({k: v for k, v in result.items() if k != 'network_config_reads'}), flush=True)
        return result

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        records = list(pool.map(run, cases))
    # Raw commands, IDs, full event output and stderr are never persisted.
    (output / 'activation-evidence.json').write_text(json.dumps(records, indent=2), encoding='utf-8')
    write_results(output, summarize(cases, records))
    if not all(r['complete'] and r.get('exit_code') == 0 for r in records):
        raise SystemExit('One or more sessions incomplete; unknowns must not count as non-activations.')


if __name__ == '__main__':
    main()
