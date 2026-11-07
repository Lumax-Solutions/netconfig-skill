#!/usr/bin/env python3
"""Paired, supplied-content smoke test. Standard library only; see README.md."""
import argparse
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

HERE = Path(__file__).resolve().parent
REFERENCES = ['SKILL.md', 'references/change-workflow.md', 'references/fortigate.md',
              'references/cisco-ios.md', 'references/mikrotik.md']
MATERIAL_HEADER = ('\n\nREFERENCE MATERIAL: apply this network-config skill to the cases. '
                   'Relevant references are included in full.\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    default_skill = Path(os.environ.get('CODEX_HOME', Path.home() / '.codex')) / 'skills' / 'network-config'
    parser.add_argument('--skill-dir', type=Path, default=os.environ.get('NETWORK_CONFIG_SKILL_DIR', default_skill))
    parser.add_argument('--output-dir', type=Path, default=os.environ.get('CODEX_TEST_OUTPUT_DIR', 'answer-quality-results'))
    parser.add_argument('--codex', default=os.environ.get('CODEX_EXECUTABLE', 'codex'))
    parser.add_argument('--model', default=None, help='Optional model pin; originals used the CLI default.')
    parser.add_argument('--workers', type=int, default=2)
    parser.add_argument('--timeout', type=int, default=600)
    parser.add_argument('--dry-run', action='store_true', help='Validate inputs and build prompts without launching Codex or writing outputs.')
    args = parser.parse_args()
    if args.workers < 1 or args.timeout < 1:
        parser.error('workers and timeout must be positive')
    skill = args.skill_dir.expanduser().resolve()
    try:
        cases = (HERE / 'cases.txt').read_text(encoding='utf-8')
        rubric = json.loads((HERE / 'rubric.json').read_text(encoding='utf-8'))
        material = MATERIAL_HEADER + '\n'.join('\nFILE ' + r + '\n' + (skill / r).read_text(encoding='utf-8') for r in REFERENCES)
        manifest = {r: hashlib.sha256((skill / r).read_bytes()).hexdigest() for r in REFERENCES}
        prompts = {}
        for arm in ['baseline', 'with-skill']:
            template = (HERE / 'prompts' / (arm + '.txt')).read_text(encoding='utf-8')
            prompts[arm] = template.replace('{{CASES}}', cases).replace('{{SKILL_MATERIAL}}', material)
        if '{{' in ''.join(prompts.values()):
            raise ValueError('Unexpanded prompt template placeholder')
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    if args.dry_run:
        print(json.dumps({'dry_run': True, 'references': len(manifest), 'checks': sum(map(len, rubric.values())),
                          'prompt_characters': {a: len(s) for a, s in prompts.items()}}))
        return
    codex = shutil.which(args.codex)
    if codex is None:
        parser.error('Codex executable not found; pass --codex or set CODEX_EXECUTABLE')
    output = args.output_dir.expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    (output / 'cases.txt').write_text(cases, encoding='utf-8')
    (output / 'rubric.json').write_text(json.dumps(rubric, indent=2), encoding='utf-8')

    def run(arm):
        (output / (arm + '-prompt.txt')).write_text(prompts[arm], encoding='utf-8')
        command = [codex, 'exec', '--ignore-user-config', '--ephemeral', '--skip-git-repo-check',
                   '-s', 'read-only', '--enable', 'skip_host_skill_discovery', '--disable', 'shell_tool',
                   '--disable', 'skill_search', '-c', 'web_search="disabled"', '-C', str(output), '--json',
                   '-o', str(output / (arm + '.md'))]
        if args.model:
            command += ['--model', args.model]
        command += ['-']
        start = time.monotonic()
        result = {'arm': arm, 'requested_model': args.model, 'complete': False}
        try:
            proc = subprocess.run(command, input=prompts[arm], capture_output=True, encoding='utf-8',
                                  errors='replace', timeout=args.timeout)
            result['exit_code'] = proc.returncode
            for line in proc.stdout.splitlines():
                try:
                    event = json.loads(line)
                except ValueError:
                    continue
                if event.get('type') == 'turn.completed':
                    result.update(complete=True, usage=event.get('usage', {}))
        except subprocess.TimeoutExpired:
            result['timeout'] = True
        except OSError:
            result['launch_failed'] = True
        result['seconds'] = round(time.monotonic() - start, 1)
        (output / (arm + '-meta.json')).write_text(json.dumps(result, indent=2), encoding='utf-8')
        # Raw events/stderr are deliberately not persisted: they may contain local paths or IDs.
        print(json.dumps(result), flush=True)
        return result

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(run, ['baseline', 'with-skill']))
    if not all(r['complete'] and r.get('exit_code') == 0 for r in results):
        raise SystemExit('Incomplete run; inspect sanitized metadata. No raw event/stderr logs were saved.')


if __name__ == '__main__':
    main()
