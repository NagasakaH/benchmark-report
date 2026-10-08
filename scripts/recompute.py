#!/usr/bin/env python3
"""Recompute published numeric summaries using standard-library Python; no inference."""
import collections
import json
import math
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'reports/terminal-bench-20261007/data'

def close(actual, expected):
    assert math.isclose(actual, expected, rel_tol=1e-9, abs_tol=1e-6), (actual, expected)

def main():
    summary = json.loads((DATA / 'aggregate.json').read_text())
    trials = json.loads((DATA / 'trials.json').read_text())
    calls = json.loads((DATA / 'api-audit.json').read_text())
    manifest = json.loads((DATA / 'tasks-manifest.json').read_text())
    labels = [r['schedule_label'] for r in trials]
    assert len(trials) == len(set(labels)) == summary['completed'] == 171
    assert summary['held'] == 9 and len(manifest['tasks']) == 20
    assert len(calls) == summary['audit']['raw_sse_requests'] == 1613
    assert len({(c['label'], c['id']) for c in calls}) == len(calls)
    tasks = {r['task'] for r in trials}
    assert len(tasks) == 19 and 'build-cython-ext' not in tasks
    assert tasks | {'build-cython-ext'} == {t['name'] for t in manifest['tasks']}
    assert collections.Counter((r['task'], r['model'], r['repetition']) for r in trials) == {
        (t, m, n): 1 for t in tasks for m in ('iq4', 'iq3', '27b') for n in (1, 2, 3)}
    known_labels = {r['label'] for r in trials}
    assert all(c['label'] in known_labels for c in calls)
    assert all(c['status'] == 200 and not c.get('error') and c['done'] and c['finish_reasons'] and c['usage'] for c in calls)
    replacements = [{'label': r['label'], 'schedule_label': r['schedule_label']} for r in trials if r['label'] != r['schedule_label']]
    assert replacements == summary['replacements'] and len(replacements) == 6
    print('| Model | Success | Rate | Mean elapsed s | Upstream input / output | Sampled GPU Wh |')
    print('| --- | --- | --- | --- | --- | --- |')
    for model, expected in summary['models'].items():
        rs = [r for r in trials if r['model'] == model]
        cs = [c for c in calls if c['model'] == model]
        assert all(c['label'] in {r['label'] for r in rs} for c in cs)
        assert len(rs) == expected['trials'] == 57
        assert len(cs) == expected['apis']
        score = sum(r['score'] for r in rs)
        close(score, expected['passed'])
        assert all(r['score'] == r['reward']['reward'] and r['score'] in (0, 1) for r in rs)
        for task in tasks:
            assert [int(r['score']) for r in sorted(rs, key=lambda r: r['repetition']) if r['task'] == task] == expected['task_scores'][task]
        elapsed = [r['elapsed_s'] for r in rs]
        close(sum(elapsed), expected['elapsed_s']['sum'])
        close(statistics.mean(elapsed), expected['elapsed_s']['mean'])
        close(statistics.median(elapsed), expected['elapsed_s']['median'])
        prep = [r['preparation_s'] for r in rs if r['preparation_s'] is not None]
        assert len(prep) == expected['preparation_s']['n']
        close(sum(prep), expected['preparation_s']['sum'])
        close(sum(elapsed) + sum(prep), expected['elapsed_plus_known_preparation_s'])
        for key in ('prompt_tokens', 'completion_tokens'):
            close(sum(c['usage'][key] for c in cs), expected['upstream_tokens'][key])
        for key, selected in [('ttft_first_s', [c for c in cs if c['first_api']]),
                              ('ttft_later_s', [c for c in cs if not c['first_api']]),
                              ('ttft_cold_first_s', [c for c in cs if c['first_api'] and c['label'] in {r['label'] for r in rs if r['preparation_s'] is not None}])]:
            close(statistics.median(c['ttft_s'] for c in selected), expected[key]['median'])
        close(sum(c['usage']['completion_tokens'] for c in cs) / sum(c['output_span_s'] for c in cs), expected['observed_output_tps'])
        timings = [c['timings'] for c in cs if c.get('timings')]
        if timings:
            for key, n, ms in [('strata_prefill_tps', 'prompt_n', 'prompt_ms'), ('strata_decode_tps', 'predicted_n', 'predicted_ms')]:
                close(sum(t[n] for t in timings) / (sum(t[ms] for t in timings) / 1000), expected[key])
        paired = [c for c in cs if len(c['vllm_deltas']) == 4]
        assert len(paired) == expected['vllm_paired_requests']
        for key in expected['vllm_deltas']:
            close(sum(c['vllm_deltas'][key] for c in paired), expected['vllm_deltas'][key])
        wh = sum(r['telemetry']['sampled_gpu_wh'] for r in rs)
        close(wh, expected['sampled_gpu_wh'])
        for key in ('span_s', 'unsampled_elapsed_s', 'post_telemetry_api_s'):
            dest = 'telemetry_span_s' if key == 'span_s' else key
            close(sum(r['telemetry'][key] for r in rs), expected[dest])
        assert all(r['telemetry']['fault_samples'] == 0 for r in rs)
        tokens = expected['upstream_tokens']
        print(f"| {model} | {score:.0f}/57 | {100*score/57:.1f}% | {statistics.mean(elapsed):.1f} | {tokens['prompt_tokens']} / {tokens['completion_tokens']} | {wh:.2f} |")
    print('\nPASS: published numeric aggregates agree. Raw SSE and per-second telemetry are not re-audited by this script.')

if __name__ == '__main__':
    main()
