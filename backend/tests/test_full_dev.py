import argparse
import json
import pytest
from scripts import evaluate_medical as runner


def test_full_dev_runs_each_dev_once_in_bounded_batches_and_never_test(tmp_path, monkeypatch):
    selected = []
    def fake(output, kb, cases, args):
        ids = args.case_ids.split(','); selected.extend(ids)
        assert len(ids) == args.limit == 2
        return {'summary': {'http_attempts': 0}, 'rows': [{'case_id': i} for i in ids], 'provider_calls': []}
    monkeypatch.setattr(runner, 'run_real', fake)
    monkeypatch.setattr(runner, 'code_hashes', lambda: {'app/example.py': 'fixed'})
    cases = [{'id': str(i), 'split': 'dev'} for i in range(20)] + [{'id': 'frozen', 'split': 'test'}]
    runner.run_full_dev(tmp_path, tmp_path/'kb.db', cases, argparse.Namespace(model_budget=16))
    report = json.loads((tmp_path/'full-dev.json').read_text(encoding='utf-8'))
    assert selected == [str(i) for i in range(20)]
    assert report['summary']['all_cases_observed'] and report['summary']['code_unchanged']
    assert len(report['batches']) == 10 and report['summary']['test40'] == 'not_run'


def test_full_dev_stops_on_code_drift_and_preserves_incomplete_checkpoint(tmp_path, monkeypatch):
    fingerprint = {'app/example.py': 'before'}
    monkeypatch.setattr(runner, 'code_hashes', lambda: dict(fingerprint))
    def fake(output, kb, cases, args):
        fingerprint['app/example.py'] = 'after'
        return {'summary': {}, 'rows': [{'case_id': i} for i in args.case_ids.split(',')], 'provider_calls': []}
    monkeypatch.setattr(runner, 'run_real', fake)
    with pytest.raises(ValueError, match='CODE_CHANGED'):
        runner.run_full_dev(tmp_path, tmp_path/'kb.db', [{'id': str(i), 'split': 'dev'} for i in range(20)],
                            argparse.Namespace(model_budget=16))
    report = json.loads((tmp_path/'full-dev.json').read_text(encoding='utf-8'))
    assert report['summary']['observed_cases'] == 2
    assert not report['summary']['all_cases_observed'] and not report['summary']['code_unchanged']
