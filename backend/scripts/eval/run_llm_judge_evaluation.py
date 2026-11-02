"""Compatibility launcher for the versioned development evaluation pipeline."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT / 'backend') not in sys.path:
    sys.path.insert(0, str(ROOT / 'backend'))

from scripts.eval.run_full_50_cases_llm_judge import main, run_evaluation


def run_llm_judge_pipeline(**kwargs):
    # Unversioned historical reports are retained, but are never resumed or rescored implicitly.
    return run_evaluation(**kwargs)


if __name__ == '__main__':
    main()
