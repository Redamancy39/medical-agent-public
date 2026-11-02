"""Build/review dev-only claim packets without models, credentials or DB writes."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding='utf-8')
from app.medical_quality import answer_template, review_answers, review_reference_points


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--report', type=Path, help='Existing real-pilot.json; dev only')
    parser.add_argument('--review', type=Path, help='Source review JSON; absent creates pending answer template')
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    bundle = json.loads(args.review.read_text(encoding='utf-8')) if args.review else None
    if args.report:
        report = json.loads(args.report.read_text(encoding='utf-8'))
        output = review_answers(report, bundle) if bundle else answer_template(report)
    elif bundle:
        output = review_reference_points(bundle)
    else:
        parser.error('provide --report or --review')
    if args.output.exists(): raise ValueError('OUTPUT_EXISTS_USE_NEW_VERSION')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'output': str(args.output), 'summary': output.get('summary'), 'clinical_review': 'not_run'}, ensure_ascii=False))


if __name__ == '__main__': main()
