import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.config import Settings
from app.database import Store
from app.providers import Gateway, ProviderError, PubMedSearch

if __name__ == '__main__':
    settings = Settings(database_path=Path(__file__).resolve().parents[2] / 'tmp/pubmed-probe.db',
                        jwt_secret='synthetic-probe-' + 'x' * 40, cloud_web_request_limit=2)
    store = Store(settings.database_path)
    store.initialize()
    gateway = Gateway(store, settings)
    try:
        documents = PubMedSearch(gateway).search('biobanking sample management', 2)
        print({'status': 'passed', 'hits': len(documents), 'http_requests': gateway.counts.get('pubmed', 0)})
    except ProviderError as error:
        print({'status': 'failed', 'safe_error_code': error.code, 'http_requests': gateway.counts.get('pubmed', 0)})
    finally:
        gateway.close()
