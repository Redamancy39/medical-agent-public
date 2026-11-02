from pathlib import Path
import sys
import argparse

import uvicorn

sys.path.insert(0, str(Path(__file__).resolve().parent))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--real', action='store_true', help='Explicitly enable DeepSeek, Mem0, local knowledge and public web tools')
    parser.add_argument('--medical', action='store_true', help='Use separate medical KB and automatic Lead routing; no frontend changes')
    args = parser.parse_args()
    if args.real or args.medical:
        from app.config import load_settings
        from app.main import create_app
        settings = load_settings()
        if args.real:
            settings = settings.model_copy(update={'deepseek_enabled': True, 'mem0_enabled': True,
            'knowledge_enabled': True, 'web_search_enabled': True, 'reranker_enabled': True,
            'run_timeout_seconds': 90, 'step_timeout_seconds': 25, 'max_model_calls': 16, 'max_tool_calls': 5,
            'max_worker_model_calls': 4, 'max_worker_iterations': 4,
            'cloud_model_request_limit': max(settings.cloud_model_request_limit, 2000),
            'cloud_memory_request_limit': max(settings.cloud_memory_request_limit, 2000),
            'cloud_web_request_limit': max(settings.cloud_web_request_limit, 500),
            'schema_repair_limit': 1})
        if args.medical:
            settings = settings.model_copy(update={'knowledge_profile': 'medical', 'knowledge_enabled': True,
                'reranker_enabled': True})
        uvicorn.run(create_app(settings), host='127.0.0.1', port=8010, access_log=False)
    else:
        uvicorn.run('app.main:create_app', factory=True, host='127.0.0.1', port=8010, access_log=False)
