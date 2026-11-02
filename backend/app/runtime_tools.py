from .agent import FakeTools
from .providers import ProviderError
from .evidence_context import expand_medical_evidence


class RuntimeTools(FakeTools):
    def __init__(self, knowledge=None, web=None):
        self.knowledge, self.web = knowledge, web

    def allowed(self, name, role):
        return super().allowed(name, role) and (name != 'search_knowledge' or self.knowledge is not None) and (name != 'deep_research' or self.web is not None)

    def execute(self, name, args, state):
        if name == 'search_knowledge':
            try:
                documents = expand_medical_evidence(self.knowledge.search(args['query'], args['max_results']),
                    query=args['query'])
            except Exception:
                raise ProviderError('KNOWLEDGE_UNAVAILABLE') from None
        elif name == 'deep_research':
            # Exactly one query and at most two public HTTP calls; no hidden LLM loop.
            documents = self.web.search(args['query'], args['max_results'])
        else:
            result = super().execute(name, args, state)
            for document in result['documents']:
                document['source'] = 'session_history' if name == 'search_history' else 'user_memory'
            documents = result['documents']
        return {'success': True, 'documents': documents, 'status': 'completed' if documents else 'no_match'}

    def close(self):
        if self.knowledge:
            self.knowledge.close()
