from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI

from docs_qa.answering.openai_answer_generator import OpenAIAnswerGenerator
from docs_qa.answering.routes import router as questions_router
from docs_qa.auth.routes import router as auth_router
from docs_qa.database import create_engine, create_session_factory
from docs_qa.embedding_model_check import ensure_embedding_model_matches
from docs_qa.ingestion.embedding import OpenAIEmbedder
from docs_qa.library.routes import router as library_router
from docs_qa.logging_setup import configure_logging, log_requests
from docs_qa.openai_client import create_openai_client
from docs_qa.problems import register_problem_handlers
from docs_qa.search.routes import router as search_router
from docs_qa.settings import Settings, get_settings


def create_app(settings: Settings) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = create_engine(settings.database.url)
        session_factory = create_session_factory(engine)
        await ensure_embedding_model_matches(session_factory, settings.embedding.model)

        # Without a key the API still starts, so documents can be uploaded and wait for it.
        client = create_openai_client(settings.openai)
        app.state.settings = settings
        app.state.session_factory = session_factory
        app.state.embedder = OpenAIEmbedder(client, settings.embedding) if client else None
        app.state.answer_generator = (
            OpenAIAnswerGenerator(client, settings.openai) if client else None
        )
        yield
        if client:
            await client.close()
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


async def _health() -> dict[str, str]:
    return {"status": "ok"}


def app() -> FastAPI:
    """Entry point for `uvicorn --factory docs_qa.main:app`."""
    configure_logging()
    return create_app(get_settings())
