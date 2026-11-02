"""Device plumbing without a GPU download; hardware timing is a separate check."""
from contextlib import nullcontext
from types import SimpleNamespace
import sys

import pytest


@pytest.mark.parametrize('requested,available,expected', [
    ('auto', False, 'cpu'), ('auto', True, 'cuda'), ('cpu', True, 'cpu'), ('cuda', True, 'cuda')])
def test_model_and_all_input_tensors_share_selected_device(monkeypatch, requested, available, expected):
    from app.knowledge import LocalReranker
    events = []
    class Tensor:
        def to(self, device):
            self.device = device
            events.append(('tensor', device))
            return self
        def reshape(self, *_): return self
        def tolist(self): return [0.2, 0.9]
    class Model:
        def to(self, device):
            self.device = device
            events.append(('model', device))
            return self
        def eval(self): return self
        def half(self): events.append(('dtype', 'fp16')); return self
        def __call__(self, **inputs):
            assert inputs and all(t.device == self.device for t in inputs.values())
            return SimpleNamespace(logits=Tensor())
    torch = SimpleNamespace(cuda=SimpleNamespace(is_available=lambda: available),
        set_num_threads=lambda _: None, inference_mode=nullcontext, sigmoid=lambda t: t)
    tokenizer = lambda *args, **kwargs: {'input_ids': Tensor(), 'attention_mask': Tensor()}
    transformers = SimpleNamespace(
        AutoTokenizer=SimpleNamespace(from_pretrained=lambda *a, **k: tokenizer),
        AutoModelForSequenceClassification=SimpleNamespace(from_pretrained=lambda *a, **k: Model()))
    monkeypatch.setitem(sys.modules, 'torch', torch)
    monkeypatch.setitem(sys.modules, 'transformers', transformers)
    reranker = LocalReranker('local-only', device=requested)
    ranked = reranker.rank('query', [{'id': 'a', 'content': 'one'}, {'id': 'b', 'content': 'two'}])
    assert reranker.device == expected and [d['id'] for d in ranked] == ['b', 'a']
    assert events.count(('tensor', expected)) == 2
    assert (('dtype', 'fp16') in events) == (expected == 'cuda')


def test_explicit_cuda_does_not_silently_use_cpu_when_unavailable(monkeypatch):
    from app.knowledge import LocalReranker
    monkeypatch.setitem(sys.modules, 'torch', SimpleNamespace(cuda=SimpleNamespace(is_available=lambda: False)))
    monkeypatch.setitem(sys.modules, 'transformers', SimpleNamespace(
        AutoTokenizer=None, AutoModelForSequenceClassification=None))
    with pytest.raises(RuntimeError, match='CUDA'):
        LocalReranker('local-only', device='cuda')
