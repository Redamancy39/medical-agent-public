"""Inspectable question/answer/score records; no credentials or raw HTTP errors."""
import csv
import json
from pathlib import Path
import re

from .evaluation_protocol import METHODS, digest


def export_artifacts(directory, report, attempts):
    directory = Path(directory)
    (directory / 'cases').mkdir(parents=True, exist_ok=True)
    rows, flat = [], []
    for method in METHODS:
        for record in report['detailed_results'][method]:
            cid = record['case_id']
            filename = re.sub(r'[^a-zA-Z0-9_-]', '_', cid)[:64] + '-' + digest(cid)[:8] + '-' + method + '.json'
            path = directory / 'cases' / filename
            payload = {**record, 'protocol_sha256': report['protocol_sha256']}
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')
            rows.append({**payload, 'detail_path': 'cases/' + filename})
            generation, score = record['generation'], record['eval_res']
            run = generation.get('run_data') or {}
            flat.append({'case_id': cid, 'method': method, 'question': record['question'],
                'answer': generation.get('answer'), 'generation_status': generation.get('generation_status'),
                'backend_status': run.get('result_status'), 'backend_error': run.get('safe_error_code'),
                'judge_status': score.get('judge_status'), 'judge_error': score.get('judge_error_code'),
                **{k: score.get(k) for k in ('action_score', 'coverage_score', 'safety_score', 'grounding_score', 'total_score', 'verdict', 'reason')},
                'dimension_reasons_json': json.dumps(score.get('cot_analysis', {}), ensure_ascii=False),
                'reference_checks_json': json.dumps(score.get('reference_checks', []), ensure_ascii=False),
                'action_checks_json': json.dumps(score.get('action_checks'), ensure_ascii=False),
                'score_adjustments_json': json.dumps(score.get('score_rule_adjustments', []), ensure_ascii=False),
                'rubric_version': score.get('rubric_version'), 'judge_requested_model': score.get('requested_model'),
                'judge_response_model': score.get('response_model'),
                'sources_json': json.dumps(generation.get('sources', []), ensure_ascii=False),
                'reviewer_status': run.get('reviewer_status'), 'omitted_claim_count': run.get('omitted_claim_count'),
                'scope_omitted_claim_count': run.get('scope_omitted_claim_count'),
                'retained_claim_count': run.get('retained_claim_count'),
                'latency_seconds': generation.get('latency'), 'model_calls': generation.get('model_calls'),
                'total_tokens': generation.get('total_tokens'), 'requested_model': generation.get('requested_model'),
                'response_model': generation.get('response_model') or json.dumps(generation.get('response_models', [])),
                'execution_origin': generation.get('execution_origin'),
                'judge_execution_origin': record.get('judge_execution_origin'), 'detail_path': 'cases/' + filename})
    with (directory / 'cases.jsonl').open('w', encoding='utf-8', newline='\n') as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False)+'\n')
    cases = {r['case_id']: r['case_snapshot'] for r in rows}
    with (directory / 'attempts.jsonl').open('w', encoding='utf-8', newline='\n') as stream:
        for attempt in attempts:
            stream.write(json.dumps({**attempt, 'question': cases[attempt['case_id']]['question']},
                ensure_ascii=False, allow_nan=False)+'\n')
    if flat:
        with (directory / 'summary.csv').open('w', encoding='utf-8-sig', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(flat[0]))
            writer.writeheader()
            # Keep verbatim text in JSON; CSV text cells must not execute spreadsheet formulas.
            for row in flat:
                writer.writerow({k: "'"+v if isinstance(v, str) and v.lstrip().startswith(('=', '+', '-', '@')) else v
                    for k, v in row.items()})
    return {'case_jsonl': str(directory / 'cases.jsonl'), 'summary_csv': str(directory / 'summary.csv'),
        'attempts_jsonl': str(directory / 'attempts.jsonl'), 'case_details_directory': str(directory / 'cases')}
