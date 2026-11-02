"""Dev retrieval by default; explicit real pilots or a bounded, batched dev20 sweep."""
import argparse
import hashlib
import json
import secrets
import sys
import time
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding='utf-8')
from app.medical_corpus import load_documents, corpus_hash
from app.medical_evaluation import validate_dataset, retrieval_score
from app.knowledge import BGEEmbedding, KnowledgeStore, LocalReranker


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--validate-only', action='store_true')
    parser.add_argument('--run-real', action='store_true', help='Explicit small DeepSeek dev pilot; no Mem0 or web')
    parser.add_argument('--pilot-only', action='store_true', help='Skip the already measured dev retrieval sweep; requires --run-real')
    parser.add_argument('--full-dev', action='store_true', help='Run all 20 dev questions once, in independent batches of two; never run test40')
    parser.add_argument('--limit', type=int, default=4, choices=range(1, 7))
    parser.add_argument('--case-ids', default='basic-01,scenario-03,comparison-03,unknown-01')
    parser.add_argument('--model-budget', type=int, default=10, choices=range(6, 17), help='Per-run total including atomization/review/rewrite; HTTP batch cap stays 40')
    args = parser.parse_args()
    if args.pilot_only and not args.run_real: parser.error('--pilot-only requires --run-real')
    if args.full_dev and (not args.run_real or args.validate_only): parser.error('--full-dev requires --run-real and cannot validate-only')
    documents = load_documents()
    cases = validate_dataset(documents=documents)
    if args.validate_only:
        print(json.dumps({'status': 'passed', 'cases': len(cases), 'dev': 20, 'test': 40, 'clinical_review': 'not_run'}))
        return
    output = ROOT / 'evaluation/medical-v1/runs' / (time.strftime('%Y%m%d-%H%M%S') + '-' + uuid4().hex[:8])
    output.mkdir(parents=True)
    embedding = BGEEmbedding(ROOT / 'data/models')
    reranker = LocalReranker('D:/rag_project/models/reranker/bge-reranker-v2-m3')
    kb_path = output / 'knowledge.db'
    rows = []
    with KnowledgeStore(kb_path, embedding, reranker) as knowledge:
        knowledge.import_documents(documents)
        for case in ([] if args.pilot_only else [c for c in cases if c['split'] == 'dev']):
            started = time.monotonic()
            hits = knowledge.search(case['question'], 5)
            rows.append({'case_id': case['id'], **retrieval_score(case, hits),
                'elapsed_seconds': time.monotonic() - started, 'hits': hits})
    eligible = [r for r in rows if r['eligible']]
    report = {'mode': 'local_dev_retrieval', 'corpus_sha256': corpus_hash(documents), 'cases': len(rows),
        'eligible_cases': len(eligible), 'no_gold_cases': len(rows)-len(eligible),
        'retrieval_sweep_status': 'not_run' if args.pilot_only else 'completed',
        'hit_at_5': sum(r['hit_at_5'] for r in eligible)/len(eligible) if eligible else None,
        'mrr_at_5': sum(r['reciprocal_rank'] for r in eligible)/len(eligible) if eligible else None,
        'mean_support_coverage_at_5': sum(r['support_coverage'] for r in eligible)/len(eligible) if eligible else None,
        'embedding': embedding.name, 'reranker': reranker.name,
        'answer_quality': 'not_run', 'clinical_review': 'not_run', 'test_answer_evaluation': 'not_run'}
    (output / 'retrieval.json').write_text(json.dumps({'summary': report, 'rows': rows}, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False))
    if args.run_real:
        if args.full_dev: run_full_dev(output, kb_path, cases, args)
        else: run_real(output, kb_path, cases, args)
    print('Report: ' + str(output))


def run_real(output, kb_path, cases, args):
    from fastapi.testclient import TestClient
    from sqlalchemy import select
    from app.config import load_settings
    from app.main import create_app
    from app.models import ProviderCall
    selected_ids = args.case_ids.split(',')
    selected = [c for c in cases if c['id'] in selected_ids and c['split'] == 'dev']
    if len(selected) != len(set(selected_ids)) or len(selected) > args.limit:
        raise ValueError('REAL_PILOT_DEV_ONLY_LIMIT')
    settings = load_settings().model_copy(update={'database_path': output / 'app.db',
        'jwt_secret': __import__('pydantic').SecretStr(secrets.token_hex(32)),
        'knowledge_profile': 'medical', 'knowledge_path': kb_path,
        'knowledge_enabled': True, 'reranker_enabled': True, 'deepseek_enabled': True,
        'mem0_enabled': False, 'web_search_enabled': False, 'maintenance_enabled': False,
        'run_timeout_seconds': 120, 'step_timeout_seconds': 25, 'max_model_calls': args.model_budget,
        'max_tool_calls': 5, 'cloud_model_request_limit': 40, 'schema_repair_limit': 1})
    app = create_app(settings)
    results = []
    with TestClient(app) as client:
        account = {'username': 'pilot-' + uuid4().hex[:8], 'password': secrets.token_hex(20)}
        client.post('/auth/register', json=account).raise_for_status()
        token = client.post('/auth/login', json=account).json()['access_token']
        headers = {'Authorization': 'Bearer ' + token}
        for case in selected:
            sid = client.post('/sessions', headers=headers, json={'title': case['id']}).json()['id']
            started = time.monotonic()
            # Only question reaches Lead; no expected actions, gold or forced topology.
            response = client.post(f'/sessions/{sid}/chat', headers=headers,
                json={'question': case['question'], 'request_id': str(uuid4())})
            response.raise_for_status()
            result = response.json()
            plan = app.state.flow.snapshot(result['run_id']).values.get('plan')
            results.append({'case_id': case['id'], 'elapsed_seconds': time.monotonic()-started,
                'actual_plan': plan, 'result': result, 'answer_review': 'pending_source_and_medical_review'})
        with app.state.store.sessions() as db:
            calls = db.scalars(select(ProviderCall)).all()
            journal = [{'provider': c.provider, 'operation': c.operation, 'status': c.status,
                'http_status': c.http_status, 'safe_error_code': c.safe_error_code,
                'usage': json.loads(c.usage_json)} for c in calls]
    report = {'mode': 'real_lead_auto', 'cases': len(results),
        'completed': sum(r['result']['result_status'] == 'completed' for r in results),
        'partial': sum(r['result']['result_status'] == 'partial' for r in results),
        'failed': sum(r['result']['result_status'] == 'failed' for r in results),
        'reviewer_completed': sum(r['result'].get('reviewer_status') == 'completed' for r in results),
        'http_attempts': len(journal), 'answer_quality': 'pending_review', 'clinical_review': 'not_run',
        'mem0': 'disabled', 'web': 'disabled', 'test_split': 'not_run'}
    (output / 'real-pilot.json').write_text(json.dumps({'summary': report, 'rows': results, 'provider_calls': journal}, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False))
    return {'summary': report, 'rows': results, 'provider_calls': journal}


def code_hashes():
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for folder in ('app', 'scripts') for p in sorted((ROOT/folder).glob('*.py'))}


def run_full_dev(output, kb_path, cases, args):
    dev = [c for c in cases if c['split'] == 'dev']
    if len(dev) != 20: raise ValueError('FULL_DEV_REQUIRES_20')
    baseline = code_hashes()
    combined = {'code_sha256': baseline, 'rows': [], 'provider_calls': [], 'batches': []}
    for offset in range(0, len(dev), 2):
        if code_hashes() != baseline: raise ValueError('FULL_DEV_CODE_CHANGED')
        folder = output / ('batch-' + str(offset//2+1).zfill(2)); folder.mkdir()
        batch_args = argparse.Namespace(**vars(args))
        batch_args.case_ids = ','.join(c['id'] for c in dev[offset:offset+2])
        batch_args.limit = 2
        batch = run_real(folder, kb_path, cases, batch_args)
        combined['rows'].extend(batch['rows']); combined['provider_calls'].extend(batch['provider_calls'])
        combined['batches'].append({'path': folder.name, **batch['summary']})
        combined['summary'] = {'mode': 'real_full_dev_auto', 'expected_cases': 20,
            'observed_cases': len(combined['rows']), 'all_cases_observed': len(combined['rows']) == 20,
            'code_unchanged': code_hashes() == baseline, 'per_run_model_budget': args.model_budget,
            'per_batch_http_cap': 40, 'max_run_model_calls': 20*args.model_budget,
            'http_attempts': len(combined['provider_calls']), 'clinical_review': 'not_run',
            'answer_quality': 'pending_independent_review', 'test40': 'not_run', 'mem0': 'disabled', 'web': 'disabled'}
        (output/'full-dev.json').write_text(json.dumps(combined, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps({'full_dev_progress': len(combined['rows']), 'of': 20}, ensure_ascii=False), flush=True)
    if not combined['summary']['code_unchanged']: raise ValueError('FULL_DEV_CODE_CHANGED')


if __name__ == '__main__':
    main()
