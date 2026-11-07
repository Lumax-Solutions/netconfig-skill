#!/usr/bin/env python3
"""Summarize sanitized activation evidence; never require raw JSONL event logs."""
import argparse
import json
import os
from pathlib import Path


def summarize(cases, records):
    by_name = {r['case']: r for r in records}
    rows = []
    for name, expected, _ in cases:
        r = by_name.get(name, {})
        complete = r.get('complete', False)
        reads = r.get('network_config_reads', [])
        successful = any(x.get('path') == 'SKILL.md' and x.get('exit_code') == 0
                         and x.get('output_characters', 0) > 100 for x in reads)
        # Incomplete/unobserved is unknown, not a negative activation result.
        loaded = successful if complete else (True if successful else None)
        rows.append({'case': name, 'expected': expected, 'complete': complete, 'loaded': loaded,
                     'network_config_reads': reads})
    return rows


def write_results(output, rows):
    output.mkdir(parents=True, exist_ok=True)
    (output / 'activation-results.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')
    lines = ['# Activation run', '', '| Case | Expected | Loaded | Complete |', '|---|---|---|---|']
    for r in rows:
        loaded = 'Unknown' if r['loaded'] is None else ('Yes' if r['loaded'] else 'No')
        lines.append(f"| {r['case']} | {'Yes' if r['expected'] else 'No'} | {loaded} | {r['complete']} |")
    (output / 'SUMMARY.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True, help='activation-evidence.json from run.py, or packaged activation-results.json')
    parser.add_argument('--cases', type=Path, default=Path(__file__).resolve().parent / 'cases.json')
    parser.add_argument('--output-dir', type=Path, default=os.environ.get('CODEX_TEST_OUTPUT_DIR', 'activation-results'))
    args = parser.parse_args()
    cases = json.loads(args.cases.read_text(encoding='utf-8'))
    rows = summarize(cases, json.loads(args.input.read_text(encoding='utf-8')))
    write_results(args.output_dir.expanduser().resolve(), rows)
    print(json.dumps({'complete': sum(r['complete'] for r in rows),
                      'intended_loaded': sum(r['loaded'] is True for r in rows if r['expected']),
                      'control_loaded': sum(r['loaded'] is True for r in rows if not r['expected'])}))


if __name__ == '__main__':
    main()
