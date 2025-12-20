# Для корректной работы приложения необходимо наличие файла .env.agent в корневой директории проекта

Структура .env.agent

```
# FastAPI
DEBUG=true

# Redis
REDIS_URL=redis://localhost:6379
REDIS_PASSWORD=
REDIS_DB=0
SESSION_TTL=600

# Qdrant
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=
QDRANT_COLLECTION=documents

# LLM
GIGACHAT_CREDENTIALS=<креды для доступа к гигачат>
MODEL=<модель линейки гигачат>

# Агент
AGENT_MAX_ITERATIONS=10
AGENT_MAX_TOKENS=4000
```