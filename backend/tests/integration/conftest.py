import os
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import httpx
import pytest
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from testcontainers.community.postgres import PostgresContainer

from docs_qa.auth.role import Role
from docs_qa.database import create_engine, create_session_factory
from docs_qa.dependencies import get_answer_generator, get_embedder
from docs_qa.ingestion.chunking import Chunker
from docs_qa.ingestion.ingestion_worker import IngestionWorker
from docs_qa.main import create_app
from docs_qa.settings import (
    AuthSettings,
    ChunkingSettings,
    DatabaseSettings,
    EmbeddingSettings,
    IngestionSettings,
    RetrievalSettings,
    Settings,
    get_settings,
)
from tests.fakes import HashingEmbedder, ScriptedAnswerGenerator

pytestmark = pytest.mark.integration

BACKEND_ROOT = Path(__file__).parents[2]
EDITOR_KEY = "test-editor-key"
READER_KEY = "test-reader-key"
POSTGRES_IMAGE = "pgvector/pgvector:0.8.7-pg17"


@pytest.fixture(scope="session")
def database_url() -> Iterator[str]:
    with PostgresContainer(POSTGRES_IMAGE, driver="asyncpg") as postgres:
        url = postgres.get_connection_url()
        os.environ["DATABASE__URL"] = url
        get_settings.cache_clear()
        command.upgrade(Config(str(BACKEND_ROOT / "alembic.ini")), "head")
        yield url


@pytest.fixture(scope="session")
def settings(database_url: str) -> Settings:
    return Settings(
        database=DatabaseSettings(url=database_url),
        embedding=EmbeddingSettings(model=HashingEmbedder.model),
        chunking=ChunkingSettings(max_words=60, overlap_words=10),
        retrieval=RetrievalSettings(min_similarity=0.2),
        ingestion=IngestionSettings(lease_seconds=60, max_attempts=2),
        auth=AuthSettings(api_keys={EDITOR_KEY: Role.EDITOR, READER_KEY: Role.READER}),
    )


@pytest.fixture(scope="session")
async def engine(settings: Settings) -> AsyncIterator[AsyncEngine]:
    engine = create_engine(settings.database.url)
    yield engine
    await engine.dispose()


@pytest.fixture
async def clean_database(engine: AsyncEngine) -> None:
    async with engine.begin() as connection:
        await connection.execute(text("TRUNCATE collections CASCADE"))


@pytest.fixture
def session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return create_session_factory(engine)


@pytest.fixture
def answer_generator() -> ScriptedAnswerGenerator:
    return ScriptedAnswerGenerator("Staff get twelve days of sick leave a year [1].")


@pytest.fixture
def app(
    settings: Settings, clean_database: None, answer_generator: ScriptedAnswerGenerator
) -> FastAPI:
    app = create_app(settings)
    app.dependency_overrides[get_embedder] = HashingEmbedder
    app.dependency_overrides[get_answer_generator] = lambda: answer_generator
    return app


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
            headers={"X-Api-Key": EDITOR_KEY},
        ) as http_client,
    ):
        yield http_client


@pytest.fixture
def worker(
    session_factory: async_sessionmaker[AsyncSession], settings: Settings
) -> IngestionWorker:
    return IngestionWorker(
        session_factory,
        HashingEmbedder(),
        Chunker(settings.chunking.max_words, settings.chunking.overlap_words),
        settings.ingestion,
    )


async def drain(worker: IngestionWorker) -> None:
    while await worker.process_next():
        pass
