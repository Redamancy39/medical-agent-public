"""One scoped read to confirm this acceptance account's cloud cleanup."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import select
from app.config import load_settings
from app.database import Store
from app.models import Conversation, User
from app.providers import Gateway, Mem0Memory, call_scope

if __name__ == '__main__':
    root = Path(__file__).resolve().parents[2]
    report = json.loads((root / 'tmp/full-flow-live-20261013-204108.json').read_text(encoding='utf-8'))
    settings = load_settings().model_copy(update={'cloud_memory_request_limit': 1})
    store = Store(settings.database_path)
    with store.sessions() as db:
        user = db.scalar(select(User).join(Conversation, Conversation.user_id == User.id).where(Conversation.id == report['session_id']))
        assert user and user.username.startswith('live_')
        user_id = user.id
    gateway = Gateway(store, settings)
    try:
        run_id = next(c['run_id'] for c in report['cases'] if c['name'] == 'corrected_memory')
        with call_scope(run_id):
            rows = Mem0Memory(gateway, settings).list_scoped(user_id)
        result = {'status': 'passed' if not rows else 'failed', 'remaining_cloud_rows': len(rows), 'mem0_requests': 1}
        (root / 'tmp/live-cleanup-verification.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
        print(result)
        assert not rows
    finally:
        gateway.close()
