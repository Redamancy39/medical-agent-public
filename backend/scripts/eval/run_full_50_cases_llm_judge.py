"""Versioned development evaluation. The filename is retained for old launch commands."""
import argparse
import json
from pathlib import Path
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT / 'backend') not in sys.path:
    sys.path.insert(0, str(ROOT / 'backend'))

from fastapi.testclient import TestClient
from app.config import load_settings
from app.main import create_app
from scripts.eval.evaluation_protocol import (
    DEFAULT_DATASET, DEFAULT_MODEL, METHODS, EvaluationCache, EvaluatorAuth, build_protocol,
    digest, generate_candidates, judge_candidates, load_cases, summarize, tree_fingerprint, attempt_usage_totals,
    evaluation_status,
)
from scripts.eval.evaluation_artifacts import export_artifacts
from scripts.eval.llm_judge import MedicalLLMJudge
from scripts.eval.run_ablation_baseline import call_zero_shot, call_naive_rag, call_ours


def run_evaluation(*, dataset=DEFAULT_DATASET, limit=None, candidate_model=DEFAULT_MODEL,
                   judge_model=DEFAULT_MODEL, max_tokens=4096, output_dir=None, resume=True,
                   dry_run=False, settings=None, transport=None):
    cases = load_cases(dataset)
    if limit is not None:
        if limit < 1:
            raise ValueError('EVALUATION_LIMIT_INVALID')
        cases = cases[:limit]
    config = None
    if not dry_run:
        config = settings or load_settings()
        if not config.deepseek_enabled or not config.knowledge_enabled:
            raise ValueError('REAL_EVALUATION_REQUIRES_MODEL_AND_KNOWLEDGE')
        config = config.model_copy(update={'deepseek_model': candidate_model, 'deepseek_temperature': 0.2,
            'model_max_tokens': max_tokens, 'mem0_enabled': False, 'maintenance_enabled': False,
            'web_search_enabled': False})
    protocol = build_protocol(cases, candidate_model=candidate_model, judge_model=judge_model,
        max_tokens=max_tokens, settings=config)
    if dry_run:
        return {'status': 'preflight_only', 'case_count': len(cases), 'protocol': protocol,
            'runtime_configuration_status': 'not_loaded', 'real_provider_calls': 0}
    directory = Path(output_dir) if output_dir else ROOT / 'docs/evaluation/runs' / digest(protocol)[:16]
    if not resume and directory.exists():
        directory = directory.with_name(directory.name + '-' + uuid4().hex[:8])
    cache = EvaluationCache(directory / 'state.json', protocol)
    # The evaluator never writes users, runs or memories into the application's real SQL database.
    database = ROOT / 'backend/data/evaluation' / uuid4().hex / 'app.db'
    config = config.model_copy(update={'database_path': database})
    app = create_app(config, transport=transport)
    app.state.evaluation_transport = transport
    with TestClient(app) as client:
        auth = EvaluatorAuth(client, 'eval_' + uuid4().hex[:12], 'Synthetic-Eval-' + uuid4().hex)
        auth.login(register=True)
        generators = {'zero_shot': lambda q: call_zero_shot(client, auth.headers, q),
            'naive_rag': lambda q: call_naive_rag(client, auth.headers, q),
            'ours': lambda q: call_ours(client, auth.headers, q, auth=auth)}
        candidates = generate_candidates(cases, cache, generators)
    judge = MedicalLLMJudge(model_name=judge_model, settings=config, transport=transport)
    results = judge_candidates(cases, candidates, cache, judge)
    # An edited corpus or prompt during execution cannot be called one comparable run.
    inputs_stable = (
        protocol['code_sha256'] == tree_fingerprint([ROOT / 'backend/app', ROOT / 'backend/scripts/eval'])
        and protocol['corpus_sha256'] == tree_fingerprint([ROOT / 'backend/knowledge'])
        and protocol['dataset_sha256'] == digest(load_cases(dataset)[:limit] if limit is not None else load_cases(dataset)))
    report = {'protocol': protocol, 'protocol_sha256': digest(protocol),
        'status': evaluation_status(results, inputs_stable),
        'input_snapshot_stable': inputs_stable,
        'summary': {m: summarize(results[m], len(cases)) for m in METHODS},
        'category_breakdown': {category: {m: summarize([r for r in results[m] if r['category'] == category],
            sum(c.get('category', '') == category for c in cases)) for m in METHODS}
            for category in sorted({c.get('category', '') for c in cases})},
        'attempt_counts': {phase: sum(r['phase'] == phase for r in cache.data['attempts'])
            for phase in ('generate', 'judge')},
        'attempt_usage_totals': attempt_usage_totals(cache.data['attempts']),
        'detailed_results': results,
        'limitations': [
            'Same-family candidate and judge models can share biases; professional review has not run.',
            'This compares system bundles with different query planning, call counts and review policies.',
            'Model judgment, backend completion, and actual source support are different measurements.',
            'Partial responses and failures remain in all-case denominators; no post-hoc case exclusions.',
            'A hash identifies the local inputs; it does not certify clinical accuracy or remote model weights.',
        ]}
    directory.mkdir(parents=True, exist_ok=True)
    report['artifacts'] = export_artifacts(directory, report, cache.data['attempts'])
    path = directory / 'report.json'
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    return {**report, 'report_path': str(path)}


def run_llm_judge_on_50_cases(max_workers=1, **kwargs):
    """Compatibility entry point; default input is dev20, not an automatic frozen-test run."""
    return run_evaluation(**kwargs)


def main():
    parser = argparse.ArgumentParser(description='Versioned development evaluation; default input is dev20.')
    parser.add_argument('--dataset', type=Path, default=DEFAULT_DATASET)
    parser.add_argument('--limit', type=int)
    parser.add_argument('--model', default=DEFAULT_MODEL)
    parser.add_argument('--judge-model', default=DEFAULT_MODEL)
    parser.add_argument('--max-tokens', type=int, choices=range(128, 8193), default=4096, metavar='128..8192')
    parser.add_argument('--output-dir', type=Path)
    parser.add_argument('--no-resume', action='store_true')
    parser.add_argument('--dry-run', action='store_true', help='No credentials, database initialization, or API calls.')
    args = parser.parse_args()
    report = run_evaluation(dataset=args.dataset, limit=args.limit, candidate_model=args.model,
        judge_model=args.judge_model, max_tokens=args.max_tokens, output_dir=args.output_dir,
        resume=not args.no_resume, dry_run=args.dry_run)
    if args.dry_run:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(json.dumps({'status': report['status'], 'report_path': report['report_path'],
            'summary': report['summary']}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
