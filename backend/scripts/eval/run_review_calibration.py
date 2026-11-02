"""Small source-entailment and scorer calibration; not a challenge benchmark."""
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT / 'backend') not in sys.path:
    sys.path.insert(0, str(ROOT / 'backend'))

from app.config import load_settings
from app.database import Store
from app.providers import DeepSeekModel, Gateway
from app.medical_reviewer import validate_review
from app.contracts import ContractViolation, contract_diagnostic
from pydantic import ValidationError
from scripts.eval.evaluation_protocol import digest, tree_fingerprint
from scripts.eval.llm_judge import MedicalLLMJudge, RUBRIC_VERSION

FIXTURES = ROOT / 'backend/calibration/reviewer-20261029/fixtures.json'


def calibration_packet(fixtures):
    # Expected labels and pairwise score expectations never enter the model payload.
    claims, position = [], 0
    for index, item in enumerate(fixtures['reviewer_cases']):
        text = item['text']
        claims.append({'index': index, 'text': text, 'start': position, 'end': position+len(text)})
        position += len(text)
    return {'question': '只根据原文判断以下句子的支持状态。', 'claims': claims,
        'evidence': fixtures['evidence'], 'policy_rules': {}, 'require_support_quotes': True,
        'corpus_scope': '固定来源片段与明确标记的合成逻辑样例。', 'evidence_packet_chars':
            sum(len(e['quote']) for e in fixtures['evidence'])}


def check_pair(pair, results):
    if any(r.get('judge_status') != 'success' for r in results):
        return {'status': 'not_scored', 'passed': None}
    metrics = pair.get('metrics', [pair['metric']])
    observed = {metric: [r[metric] for r in results] for metric in metrics}
    passed = all(abs(left-right) <= pair['tolerance'] if pair['check'] == 'equivalent'
        else left-right >= pair['margin'] for left,right in observed.values())
    return {'status': 'scored', 'passed': passed, 'metrics': observed}


def scope_packet(trial, fixtures):
    packet = calibration_packet(fixtures)
    packet.update(question=trial['question'], claims=[], require_scope_review=True)
    position = 0
    for index, item in enumerate(trial['claims']):
        text = item['text']
        packet['claims'].append({'index': index, 'text': text, 'start': position, 'end': position+len(text)})
        position += len(text)
    packet['policy_rules'] = {'unknown': '本次资料不足时说明边界，不编造结论。',
        'educational_scope': '本系统不能远程确诊，不替代医生个体化判断。'}
    return packet


def run_calibration(*, output_dir=None, fixtures_path=FIXTURES, settings=None, transport=None, dry_run=False):
    fixtures = json.loads(Path(fixtures_path).read_text(encoding='utf-8'))
    packet = calibration_packet(fixtures)
    if dry_run:
        return {'status': 'preflight_only', 'reviewer_cases': len(packet['claims']),
            'judge_pairs': len(fixtures['judge_pairs']), 'scope_trials': len(fixtures.get('scope_trials', [])),
            'real_provider_calls': 0}
    settings = (settings or load_settings()).model_copy(update={'deepseek_model': 'deepseek-chat',
        'deepseek_temperature': 0.0, 'knowledge_profile': 'medical', 'mem0_enabled': False,
        'web_search_enabled': False, 'maintenance_enabled': False})
    out = Path(output_dir) if output_dir else ROOT / 'docs/evaluation/reviewer-calibration-20261029' / uuid4().hex[:8]
    out.mkdir(parents=True, exist_ok=False)
    store = Store(ROOT / 'backend/data/calibration' / uuid4().hex / 'app.db')
    store.initialize()
    gateway = Gateway(store, settings, transport)
    model = DeepSeekModel(gateway, settings)
    report = {'created_at': datetime.now(timezone.utc).isoformat(), 'fixtures_sha256': digest(fixtures),
        'code_sha256': tree_fingerprint([ROOT / 'backend/app', ROOT / 'backend/scripts/eval']),
        'rubric_version': RUBRIC_VERSION, 'reference_status': fixtures['reference_status'],
        'review_attempts': [], 'review_results': [], 'scope_results': [], 'judge_pairs': [], 'clinical_review': 'not_run'}

    def save():
        (out / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

    try:
        payload = {'question': packet['question'], 'review_packet': packet}
        output = None
        for attempt in range(2):
            raw = model.review(payload)
            record = {'attempt': attempt+1, 'output': raw}
            try:
                output = validate_review(raw, packet)
            except (ContractViolation, ValidationError) as error:
                diagnostic = contract_diagnostic('review', error, 'REVIEW_INVALID')
                record.update(status='contract_failed', diagnostic=diagnostic)
                payload['contract_repair'] = diagnostic
            else:
                record['status'] = 'validated'
            report['review_attempts'].append(record)
            save()
            if output is not None:
                break
        if output is not None:
            by_index = {c.index: c for c in output.claims}
            report['review_results'] = [{**item, 'review': by_index[i].model_dump(),
                'passed': (by_index[i].support_status == 'supported') == item['expected_supported']}
                for i, item in enumerate(fixtures['reviewer_cases'])]
        for trial in fixtures.get('scope_trials', []):
            trial_packet = scope_packet(trial, fixtures)
            payload = {'review_packet': trial_packet}
            record = {'id': trial['id'], 'question': trial['question'], 'attempts': [], 'results': []}
            for attempt in range(2):
                raw = model.review(payload)
                observation = {'attempt': attempt+1, 'output': raw}
                try:
                    typed = validate_review(raw, trial_packet)
                except (ContractViolation, ValidationError) as error:
                    diagnostic = contract_diagnostic('review', error, 'REVIEW_INVALID')
                    observation.update(status='contract_failed', diagnostic=diagnostic)
                    payload['contract_repair'] = diagnostic
                else:
                    observation['status'] = 'validated'
                    by_index = {c.index: c for c in typed.claims}
                    record['results'] = [{**item, 'review': by_index[i].model_dump(),
                        'passed': (by_index[i].scope_status in item['expected_scope'] and
                            (by_index[i].support_status == 'supported') == item['expected_supported'])}
                        for i, item in enumerate(trial['claims'])]
                record['attempts'].append(observation)
                if observation['status'] == 'validated': break
            report['scope_results'].append(record)
            save()
        judge = MedicalLLMJudge(settings=settings, transport=transport)
        for pair in fixtures['judge_pairs']:
            case = {k: pair[k] for k in ('question', 'reference_points')}
            results = [judge.evaluate_single(case, answer, pair['sources']) for answer in pair['answers']]
            report['judge_pairs'].append({**pair, 'outputs': results, 'check_result': check_pair(pair, results)})
            save()
        report['summary'] = {'reviewer_passed': sum(r['passed'] for r in report['review_results']),
            'reviewer_total': len(fixtures['reviewer_cases']),
            'reviewer_contract_status': 'validated' if output is not None else 'failed',
            'judge_pairs_passed': sum(p['check_result']['passed'] is True for p in report['judge_pairs']),
            'judge_pairs_total': len(fixtures['judge_pairs'])}
        report['summary'].update(scope_passed=sum(r['passed'] for t in report['scope_results'] for r in t['results']),
            scope_total=sum(len(t['claims']) for t in fixtures.get('scope_trials', [])))
    except Exception as error:
        report['execution_error'] = {'type': type(error).__name__, 'safe_code': getattr(error, 'code', 'CALIBRATION_FAILED')}
        raise
    finally:
        from app.models import ProviderCall
        from sqlalchemy import select
        with store.sessions() as db:
            report['review_provider_calls'] = [{'operation': r.operation, 'status': r.status,
                'elapsed_seconds': r.elapsed_seconds, 'usage': json.loads(r.usage_json)}
                for r in db.scalars(select(ProviderCall).order_by(ProviderCall.created_at))]
        save()
        gateway.close()
        store.engine.dispose()
    return {'report_path': str(out / 'report.json'), 'summary': report['summary']}


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--output-dir', type=Path)
    parser.add_argument('--fixtures', type=Path, default=FIXTURES)
    args = parser.parse_args()
    print(json.dumps(run_calibration(dry_run=args.dry_run, output_dir=args.output_dir,
        fixtures_path=args.fixtures), ensure_ascii=False, indent=2))
