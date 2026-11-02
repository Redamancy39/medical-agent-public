"""Validate a readable Dot JSON export; no network, corpus updates or model calls."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding='utf-8')
from app.medical_handoff import stage_handoff, HandoffBatch
from pydantic import ValidationError


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path)
    parser.add_argument('--schema', action='store_true')
    args = parser.parse_args()
    if args.schema:
        print(json.dumps(HandoffBatch.model_json_schema(), ensure_ascii=False, indent=2))
        return
    if not args.input or args.input.suffix.lower() != '.json': parser.error('provide --input with a .json export')
    if args.input.stat().st_size > 256000: parser.error('handoff exceeds 256000 bytes; export smaller batches')
    try:
        payload = json.loads(args.input.read_text(encoding='utf-8-sig'))
        result = stage_handoff(payload, ROOT / 'knowledge/medical-handoff/inbox')
    except ValidationError as error:
        # Never dump user-provided inputs in validation errors.
        print(json.dumps({'status': 'rejected', 'error': 'HANDOFF_SCHEMA_INVALID',
            'fields': [{'location': '.'.join(map(str, e['loc'])), 'type': e['type']} for e in error.errors()]}))
        raise SystemExit(1)
    except (ValueError, OSError) as error:
        allowed = {'UNKNOWN_CASE_ID', 'TEST_AUDIT_PAUSED', 'UNKNOWN_POLICY_RULE', 'BATCH_ID_CONTENT_CHANGED'}
        print(json.dumps({'status': 'rejected', 'error': str(error) if str(error) in allowed else 'HANDOFF_READ_OR_VALIDATION_FAILED'}))
        raise SystemExit(1)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__': main()
