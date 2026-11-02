import importlib.util
from pathlib import Path
import pytest

path = Path(__file__).resolve().parents[1] / 'scripts/fetch_medical_sources.py'
spec = importlib.util.spec_from_file_location('medical_fetch', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

def test_nested_lists_conditions_and_table_headers_survive():
    raw = '<h1>Test</h1><div id="topic-summary"><h2>Risk</h2><ul><li>Higher risk if:</li><ul><li>Diabetes</li><li>High pressure</li></ul></ul><p>' + 'x' * 300 + '</p><table><tr><th>Category</th><th>Value</th></tr><tr><td>Normal</td><td>Below 5.7%</td></tr></table></div><div>A.D.A.M. private content</div>'
    _, body = module.extract_body(raw, 'topic_summary')
    assert 'Higher risk if:' in body and 'Diabetes' in body and 'High pressure' in body
    assert 'Category | Value' in body and 'Normal | Below 5.7%' in body
    assert 'private content' not in body

def test_medical_test_excludes_references_and_unsupported_body():
    raw = '<h1>Test</h1><article><section><div class="mp-content"><h2>Meaning</h2><p>' + 'body ' * 80 + '</p></div><div class="mp-refs mp-content">licensed reference titles</div></section></article>'
    _, body = module.extract_body(raw, 'medical_test')
    assert 'Meaning' in body and 'licensed reference titles' not in body
    with pytest.raises(ValueError): module.extract_body(raw, 'topic_summary')
