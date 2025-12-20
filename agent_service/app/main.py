from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time
import uuid

from config import settings
from models import AgentRequest, AgentResponse, RAGRequest, RAGResponse
from state_manager import state_manager
from agent import Agent
from rag_client import rag_client

# Создаем приложение
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене указать конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Middleware для логирования
@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = str(uuid.uuid4())
    start_time = time.time()

    response = await call_next(request)

    process_time = time.time() - start_time
    print(f"{request.method} {request.url.path} - {response.status_code} - {process_time:.2f}s - {request_id}")

    return response


# Зависимости
async def get_session_id(x_session_id: str = Header(None, alias="X-Session-Id")) -> str:
    """Получить или создать ID сессии"""
    if not x_session_id:
        # Генерируем новую сессию
        session_id, _ = await state_manager.create_state()
        return session_id
    return x_session_id


# Эндпоинты
@app.post("/invoke", response_model=AgentResponse)
async def invoke_agent(
        request: AgentRequest,
        session_id: str = Depends(get_session_id)
):
    """
    Основной эндпоинт для взаимодействия с агентом
    """
    try:
        # Получаем или создаем состояние
        state = await state_manager.get_state(session_id)
        if not state:
            session_id, state = await state_manager.create_state(session_id)

        # Обрабатываем запрос агентом
        result = await Agent.process(
            query=request.query,
            state=state
        )

        # Сохраняем обновленное состояние
        await state_manager.save_state(session_id, state)

        return AgentResponse(
            response=result["response"],
            sources=result.get("sources", []),
            session_id=session_id,
            used_tools=result.get("used_tools", [])
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")


@app.post("/rag/search", response_model=RAGResponse)
async def search_documents(request: RAGRequest):
    """
    Поиск по векторной БД (внутренний эндпоинт)
    """
    try:
        response = await rag_client.search(request)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAG search error: {str(e)}")


@app.post("/session/reset")
async def reset_session(session_id: str = Depends(get_session_id)):
    """
    Сбросить состояние сессии
    """
    success = await state_manager.reset_state(session_id)
    if success:
        return {"message": "Session reset successfully", "session_id": session_id}
    else:
        raise HTTPException(status_code=500, detail="Failed to reset session")


@app.get("/health")
async def health_check():
    """Проверка здоровья сервиса"""
    status = {
        "status": "healthy",
        "timestamp": time.time(),
        "services": {
            "redis": False,
            "qdrant": False,
            "llm": Agent.llm_client is not None
        }
    }

    # Проверяем Redis
    try:
        await state_manager.redis_client.ping()
        status["services"]["redis"] = True
    except:
        status["services"]["redis"] = False

    # Проверяем Qdrant
    try:
        status["services"]["qdrant"] = await rag_client.health_check()
    except:
        status["services"]["qdrant"] = False

    # Если какой-то сервис недоступен
    if not all(status["services"].values()):
        status["status"] = "degraded"

    return status


# Обработчики событий
@app.on_event("startup")
async def startup_event():
    """Инициализация при запуске"""
    print(f"🚀 Starting {settings.APP_NAME} v{settings.APP_VERSION}")

    # Подключаемся к Redis
    await state_manager.connect()

    # Подключаемся к Qdrant
    await rag_client.connect()

    # Инициализируем агента
    await Agent.connect()

    print("✅ All services initialized")


@app.on_event("shutdown")
async def shutdown_event():
    """Очистка при завершении"""
    await state_manager.disconnect()
    print("👋 Shutting down")


# Обработка ошибок
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"}
    )


# Корневой эндпоинт
@app.get("/")
async def root():
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "endpoints": {
            "POST /invoke": "Interact with the agent_service",
            "POST /rag/search": "Search documents (internal)",
            "POST /session/reset": "Reset session state",
            "GET /health": "Health check"
        }
    }