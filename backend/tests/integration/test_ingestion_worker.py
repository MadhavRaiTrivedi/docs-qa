import uuid
from collections.abc import Awaitable, Callable, Sequence
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select

from docs_qa.ingestion.chunking import Chunker
from docs_qa.ingestion.embedding import Embedder
from docs_qa.ingestion.ingestion_worker import IngestionWorker
from docs_qa.ingestion.parsing import MarkdownParser
from docs_qa.library.enums import DocumentStatus, FileFormat
from docs_qa.library.models import Chunk, Collection, Document, DocumentFile
from tests.fakes import HashingEmbedder
from tests.integration.sample_documents import LEAVE_POLICY

pytestmark = pytest.mark.integration


class Clock:
    def __init__(self) -> None:
        self.now = datetime(2026, 10, 5, 12, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.now


class InterruptedEmbedder(HashingEmbedder):
    """Runs `interruption` in the middle of ingestion, as if this worker had stalled there."""

    def __init__(self, interruption: Callable[[], Awaitable[None]]) -> None:
        self._interruption = interruption

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        await self._interruption()
        return await super().embed_documents(texts)


class CrashingEmbedder(HashingEmbedder):
    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        raise ConnectionError("embedding service is down")


@pytest.fixture
async def document_id(clean_database, session_factory) -> uuid.UUID:
    async with session_factory() as session:
        collection = Collection(id=uuid.uuid4(), name="Handbook")
        document = Document.upload(collection.id, "leave.md", FileFormat.MARKDOWN, LEAVE_POLICY)
        session.add_all([collection, document])
        session.add(DocumentFile(document_id=document.id, content=LEAVE_POLICY))
        await session.commit()
        return document.id


@pytest.fixture
def clock() -> Clock:
    return Clock()


@pytest.fixture
def make_worker(session_factory, settings, clock) -> Callable[[Embedder], IngestionWorker]:
    def make(embedder: Embedder) -> IngestionWorker:
        chunker = Chunker(settings.chunking.max_words, settings.chunking.overlap_words)
        return IngestionWorker(session_factory, embedder, chunker, settings.ingestion, clock)

    return make


async def load(session_factory, document_id: uuid.UUID) -> tuple[Document, int]:
    async with session_factory() as session:
        document = await session.get(Document, document_id)
        chunk_count = await session.scalar(
            select(func.count()).where(Chunk.document_id == document_id)
        )
    assert document is not None
    return document, chunk_count or 0


async def test_document_under_a_live_lease_is_not_claimed_again(document_id, make_worker) -> None:
    other_worker = make_worker(HashingEmbedder())
    other_claimed: list[bool] = []

    async def other_worker_polls() -> None:
        other_claimed.append(await other_worker.process_next())

    await make_worker(InterruptedEmbedder(other_worker_polls)).process_next()

    assert other_claimed == [False]


async def test_result_of_a_worker_whose_lease_expired_is_discarded(
    document_id, make_worker, session_factory, settings, clock
) -> None:
    fast_worker = make_worker(HashingEmbedder())

    async def lease_expires_and_fast_worker_finishes() -> None:
        clock.now += timedelta(seconds=settings.ingestion.lease_seconds + 1)
        assert await fast_worker.process_next()

    slow_worker = make_worker(InterruptedEmbedder(lease_expires_and_fast_worker_finishes))
    await slow_worker.process_next()

    document, chunk_count = await load(session_factory, document_id)
    chunker = Chunker(settings.chunking.max_words, settings.chunking.overlap_words)
    assert document.status is DocumentStatus.READY
    assert document.attempts == 2
    assert chunk_count == len(chunker.split(MarkdownParser().parse(LEAVE_POLICY).sections))


async def test_crashed_ingestion_is_retried_after_the_lease_expires(
    document_id, make_worker, session_factory, settings, clock
) -> None:
    with pytest.raises(ConnectionError):
        await make_worker(CrashingEmbedder()).process_next()

    clock.now += timedelta(seconds=settings.ingestion.lease_seconds + 1)
    await make_worker(HashingEmbedder()).process_next()

    document, _ = await load(session_factory, document_id)
    assert document.status is DocumentStatus.READY


async def test_document_fails_once_its_last_attempt_expires(
    document_id, make_worker, session_factory, settings, clock
) -> None:
    crashing_worker = make_worker(CrashingEmbedder())
    for _ in range(settings.ingestion.max_attempts):
        with pytest.raises(ConnectionError):
            await crashing_worker.process_next()
        clock.now += timedelta(seconds=settings.ingestion.lease_seconds + 1)

    assert not await crashing_worker.process_next()

    document, _ = await load(session_factory, document_id)
    assert document.status is DocumentStatus.FAILED
    assert document.failure_reason == f"Gave up after {settings.ingestion.max_attempts} attempts."
