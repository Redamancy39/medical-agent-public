"""Explicit fixed-source Reviewer pilot. No retrieval, frozen test or gold in provider payload."""
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
from app.medical_corpus import load_documents
from app.medical_reviewer import build_packet, validate_review
from app.contracts import contract_diagnostic, ContractViolation
from app.providers import ProviderError
from pydantic import ValidationError


def calibration_packet(fixtures):
    sources = []
    for doc in load_documents():
        if doc['id'] not in fixtures.get('document_ids', ['nlm-a1c-test', 'nlm-blood-glucose']): continue
        section = doc['sections'][0]
        sources.append({'id': doc['id']+'-calibration', 'document_id': doc['id'], 'version': doc['version'],
            'source_sha256': doc['source_sha256'], 'start': section['start'], 'end': section['end'],
            'content': section['text'], 'source_spans': section['source_spans'], 'url': doc['url']})
    packet = build_packet('逐条核对这些独立断言的原文或项目规则支持，不把一条的错误当成另一条的证据。',
                          ''.join(c['text'] for c in fixtures['cases']), sources)
    assert len(packet['claims']) == len(fixtures['cases'])
    return packet


def calibration_calls(model, packet, outputs, attempts):
    for offset in range(0, len(packet['claims']), 10):
        batch = {**packet, 'claims': [{**c, 'index': i} for i,c in enumerate(packet['claims'][offset:offset+10])]}
        payload = {'review_packet': batch}
        for repair in range(2):
            attempt = {'global_offset': offset, 'format_repair': bool(repair)}
            attempts.append(attempt)
            try:
                output = validate_review(model.review(payload), batch)
            except (ContractViolation, ValidationError, ProviderError) as error:
                diagnostic = contract_diagnostic('calibration', error, 'REVIEW_INVALID')
                attempt.update(status='failed', diagnostic=diagnostic)
                if repair or isinstance(error, ProviderError): raise
                payload['contract_repair'] = diagnostic
            else:
                attempt.update(status='completed')
                outputs.extend(v.model_copy(update={'index': v.index+offset}) for v in output.claims)
                break


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-real', action='store_true')
    parser.add_argument('--fixtures', type=Path, default=ROOT/'evaluation/reviewer-calibration-v1/fixtures.json')
    args = parser.parse_args()
    fixture_path = args.fixtures.resolve()
    fixtures = json.loads(fixture_path.read_text(encoding='utf-8'))
    packet = calibration_packet(fixtures)
    if not args.run_real:
        print(json.dumps({'status': 'fixtures_valid', 'cases': len(packet['claims']), 'model': 'not_run'})); return
    from pydantic import SecretStr
    from sqlalchemy import select
    from app.config import load_settings
    from app.database import Store
    from app.models import ProviderCall
    from app.providers import Gateway, DeepSeekModel
    folder = fixture_path.parent/'runs'/(time.strftime('%Y%m%d-%H%M%S')+'-'+uuid4().hex[:8])
    folder.mkdir(parents=True)
    settings = load_settings().model_copy(update={'database_path': folder/'calibration.db',
        'jwt_secret': SecretStr(secrets.token_hex(32)), 'cloud_model_request_limit': 2*((len(packet['claims'])+9)//10),
        'mem0_enabled': False, 'web_search_enabled': False, 'maintenance_enabled': False})
    store = Store(settings.database_path); store.initialize()
    gateway = Gateway(store, settings)
    try:
        model, outputs, attempts, failure = DeepSeekModel(gateway, settings), [], [], None
        try: calibration_calls(model, packet, outputs, attempts)
        except Exception as error: failure = contract_diagnostic('calibration', error, 'CALIBRATION_FAILED')
        rows = []
        for verdict in sorted(outputs, key=lambda c: c.index):
            expected = fixtures['cases'][verdict.index]
            accepted = verdict.support_status == 'supported'
            rows.append({**expected, **verdict.model_dump(), 'actual_accept': accepted,
                         'accept_matches': accepted == expected['accept'], 'kind_matches': verdict.kind == expected['kind']})
        with store.sessions() as db:
            journal = [{'operation': c.operation, 'status': c.status, 'usage': json.loads(c.usage_json)}
                       for c in db.scalars(select(ProviderCall)).all()]
        positives = [r for r in rows if r['accept']]; negatives = [r for r in rows if not r['accept']]
        summary = {'status': 'failed' if failure else 'completed', 'error': failure,
            'cases': len(rows), 'expected_cases': len(fixtures['cases']),
            'false_rejections': sum(not r['actual_accept'] for r in positives) if positives else None,
            'false_acceptances': sum(r['actual_accept'] for r in negatives) if negatives else None,
            'kind_matches': sum(r['kind_matches'] for r in rows) if rows else None,
            'http_attempts': len(journal), 'fixture_sha256': hashlib.sha256(fixture_path.read_bytes()).hexdigest(),
            'clinical_review': 'not_run', 'generalization': 'not_established', 'test40': 'not_run'}
        (folder/'calibration.json').write_text(json.dumps({'summary': summary, 'rows': rows,
            'packet': packet, 'attempts': attempts, 'provider_calls': journal}, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps(summary)); print('Report: '+str(folder))
        if failure: raise SystemExit(1)
    finally: gateway.close()


if __name__ == '__main__': main()
