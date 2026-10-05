from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import APIRouter, FastAPI
from openai import AsyncOpenAI

from docs_qa.answering.openai_answer_generator import OpenAIAnswerGenerator
from docs_qa.answering.routes import router as questions_router
from docs_qa.auth.routes import router as auth_router
from docs_qa.database import create_engine, create_session_factory
from docs_qa.embedding_model_check import ensure_embedding_model_matches
from docs_qa.ingestion.embedding import OllamaEmbedder
from docs_qa.library.routes import router as library_router
from docs_qa.logging_setup import configure_logging, log_requests
from docs_qa.problems import register_problem_handlers
from docs_qa.search.routes import router as search_router
from docs_qa.settings import Settings, get_settings


def create_app(settings: Settings) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = create_engine(settings.database.url)
        session_factory = create_session_factory(engine)
        await ensure_embedding_model_matches(session_factory, settings.embedding.model)

        async with httpx.AsyncClient() as http_client:
            app.state.settings = settings
            app.state.session_factory = session_factory
            app.state.embedder = OllamaEmbedder(http_client, settings.embedding)
            app.state.answer_generator = _answer_generator(settings)
            yield
        await engine.dispose()

    app = FastAPI(
        title="Docs Q&A",
        lifespan=lifespan,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        redoc_url=None,
    )
    app.middleware("http")(log_requests)
    register_problem_handlers(app)

    api = APIRouter(prefix="/api")
    api.add_api_route("/health", _health, methods=["GET"], tags=["health"])
    for router in (auth_router, library_router, search_router, questions_router):
        api.include_router(router)
    app.include_router(api)
    return app


def _answer_generator(settings: Settings) -> OpenAIAnswerGenerator | None:
    if settings.openai.api_key is None:
        return None
    client = AsyncOpenAI(
        api_key=settings.openai.api_key.get_secret_value(),
        timeout=settings.openai.timeout_seconds,
    )
    return OpenAIAnswerGenerator(client, settings.openai)


async def _health() -> dict[str, str]:
    return {"status": "ok"}


def app() -> FastAPI:
    """Entry point for `uvicorn --factory docs_qa.main:app`."""
    configure_logging()
    return create_app(get_settings())
