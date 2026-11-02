"""Verify the final Dot candidate delivery locally; never admit it into the formal corpus."""
import hashlib
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding='utf-8')
from app.medical_handoff import stage_handoff


def digest(data): return hashlib.sha256(data).hexdigest()
def read(path): return json.loads(path.read_text(encoding='utf-8'))


def verify(folder):
    delivered = folder/'deliveries'
    file_receipts = read(delivered/'cloud-file-receipts-m.json')
    for item in file_receipts:
        path = (folder/item['path']).resolve()
        assert path.is_relative_to(folder.resolve()), 'RECEIPT_PATH_INVALID'
        data = path.read_bytes()
        assert digest(data) == item['sha256'] and len(data) == item['bytes'], 'DELIVERED_BYTES_INVALID'
    records = [r for n in ('cumulative-source-records-01.json', 'cumulative-source-records-02.json')
               for r in read(delivered/n)['source_records']]
    bodies, receipts, baseline = {}, [], []
    for source in records:
        sid = source['source_id']
        assert sid not in bodies, 'DUPLICATE_SOURCE_ID'
        assert source['professional_review'] == 'pending'
        if source['batch_id'] == 'baseline20':
            path = ROOT.parent/source['archive_relative_path']
            raw = path.read_bytes()
            assert digest(raw) == source['snapshot_raw_bytes_sha256']
            text = path.read_text(encoding='utf-8')  # Existing CRLF bytes stay unchanged.
            baseline.append({'source_id': sid, 'snapshot_bytes_sha256': digest(raw), 'normalized_sha256': digest(text.encode())})
        else:
            paths = sorted((folder/'raw').glob(sid+'-*.txt'))
            if source.get('body_part_references'):
                paths = [next((folder/'raw').glob(sid+'-part'+str(i+1)+'-*.txt'))
                         for i in range(len(source['body_part_references']))]
            else:
                paths = [p for p in paths if p.name == sid+'-'+source['normalized_text_sha256'][:12]+'.txt']
            assert paths, 'BODY_FILE_MISSING'
            text = ''.join(p.read_bytes().decode('utf-8') for p in paths)
            assert '\r' not in text, 'DELIVERED_TEXT_NOT_LF'
            receipts.append({'source_id': sid, 'source_family_id': source['source_family_id'],
                'paths': [str(p.relative_to(ROOT)) for p in paths], 'sha256': digest(text.encode()),
                'physical_files': len(paths), 'target_eligible_from_dot': source['target_eligible'],
                'local_admission': 'pending_source_license_and_professional_review'})
        assert digest(text.encode()) == source['normalized_text_sha256'], 'NORMALIZED_HASH_INVALID'
        bodies[sid] = {**source, 'text': text}
    policy_path = ROOT/'evaluation/medical-v1/policy.json'
    policy, policy_hash = read(policy_path), digest(policy_path.read_bytes())
    def check_policy(item):
        assert item['policy_file_sha256'] == policy_hash and item['policy_version'] == policy['version']
        assert item['rule_text'] == policy['rules'][item['rule_id']]
    schema = read(delivered/'candidate-schema.json')
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    candidate_index = read(delivered/'candidate-final-index.json')
    questions, evidence_count, point_count = [], 0, 0
    for i, batch in enumerate(candidate_index['batches']):
        path = delivered/('candidate-b01.json' if i == 0 else batch['batch_id']+'.json')
        assert digest(path.read_bytes()) == batch['sha256'] and path.stat().st_size == batch['bytes']
        payload = read(path); validator.validate(payload)
        for question in payload['questions']:
            assert 'split' not in question and question['professional_review'] == 'pending'
            for item in question['action_policy_evidence']: check_policy(item)
            evidence = {e['evidence_id']: e for e in question['evidence']}
            assert len(evidence) == len(question['evidence'])
            for item in evidence.values():
                source = bodies[item['source_id']]
                assert item['normalized_text_sha256'] == source['normalized_text_sha256']
                assert item['source_family_id'] == source['source_family_id'] and item['url'] == source['original_url']
                assert item['quote'].strip() and item['quote'] in source['text'], 'CANDIDATE_QUOTE_INVALID'
                evidence_count += 1
            for point in question['reference_points']:
                assert set(point['evidence_ids']) <= evidence.keys()
                if point['reference_kind'] == 'medical_fact': assert point['evidence_ids']
                for item in point['policy_evidence']: check_policy(item)
                point_count += 1
            questions.append(question)
    ids = [q['question_id'] for q in questions]
    assert len(ids) == len(set(ids)) == 60 and point_count == 184
    staged = [stage_handoff(read(path), ROOT/'knowledge/medical-handoff/inbox')
              for path in sorted(delivered.glob('*-medical-handoff-v1.json'))]
    families = {s['source_family_id'] for s in records}
    eligible = {s['source_family_id'] for s in records if s['target_eligible']}
    quarantined = [s['source_id'] for s in records if not s['target_eligible']]
    assert len(families) == 102 and len(eligible) == 100 and len(baseline) == 20
    summary = {'schema_version': 'dot-local-final-receipt-m-v1', 'downloaded_file_hashes_passed': len(file_receipts),
        'baseline_source_documents_verified': len(baseline), 'new_source_documents': len(receipts),
        'new_physical_body_files': sum(r['physical_files'] for r in receipts),
        'retained_source_families': len(families), 'target_eligible_families_from_dot': len(eligible),
        'clinical_rule_quarantined_source_ids': quarantined, 'candidate_questions': len(questions),
        'candidate_families_literal': len({q['family_id'] for q in questions}), 'candidate_reference_points': point_count,
        'candidate_evidence_records': evidence_count, 'candidate_full_jsonschema_validation': 'passed',
        'candidate_quote_hash_policy_validation': 'passed', 'candidate_family_semantic_isolation': 'not_run',
        'license_independent_review': 'not_run', 'clinical_review': 'not_run',
        'formal_corpus_update': 'not_applied', 'frozen_dataset_update': 'not_applied', 'vectorization': 'not_run',
        'research_schedule_disabled': 'reported_by_dot_hash_verified_cloud_file_not_independent_scheduler_query'}
    (folder/'local-receipt-m.json').write_text(json.dumps({'summary': summary, 'bodies': receipts,
        'baseline': baseline, 'handoffs': staged}, ensure_ascii=False, indent=2), encoding='utf-8')
    return summary


if __name__ == '__main__':
    print(json.dumps(verify(ROOT/'knowledge/medical-dot'), ensure_ascii=False))
