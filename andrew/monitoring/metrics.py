from prometheus_client import Counter, Histogram, Gauge, generate_latest, REGISTRY
from prometheus_client.exposition import MetricsHandler
import time

# Определяем метрики
QUERY_COUNTER = Counter(
    'agent_queries_total',
    'Total number of queries processed',
    ['status', 'llm_model']
)

RESPONSE_TIME = Histogram(
    'agent_response_time_seconds',
    'Response time for agent queries',
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)

ARTICLES_FOUND = Histogram(
    'rag_articles_found_per_query',
    'Number of articles found per query',
    buckets=[0, 1, 3, 5, 10]
)

LLM_CALL_DURATION = Histogram(
    'llm_call_duration_seconds',
    'Duration of LLM API calls',
    ['operation']
)

# Метрики состояния системы
QDRAIN_STATUS = Gauge('qdrant_connection_status', 'Qdrant connection status (1=up, 0=down)')
LLM_STATUS = Gauge('llm_provider_status', 'LLM provider status (1=up, 0=down)')
ACTIVE_USERS = Gauge('active_users_current', 'Current number of active users')