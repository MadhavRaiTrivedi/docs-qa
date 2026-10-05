import asyncio
import logging
import uuid
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import and_, delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from docs_qa.ingestion.chunking import ChunkDraft, Chunker
from docs_qa.ingestion.embedding import Embedder
from docs_qa.ingestion.parsing import DocumentParseError, parser_for
from docs_qa.library.enums import DocumentStatus, FileFormat
from docs_qa.library.errors import LeaseLostError
from docs_qa.library.models import Chunk, Document, DocumentFile
from docs_qa.settings import IngestionSettings

logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True)
class Claim:
    document_id: UUID
    collection_id: UUID
    lease_token: UUID
    file_name: str
    file_format: FileFormat
    content: bytes


@dataclass(frozen=True)
class IngestedChunks:
    drafts: list[ChunkDraft]
    embeddings: list[list[float]]
    page_count: int | None


def embedding_input(file_name: str, draft: ChunkDraft) -> str:
    """Prefixes the chunk with where it comes from, so a chunk like "It is 12 days" is still
    found by a question about sick leave when the heading carries that context."""
    location = draft.location.describe()
    header = f"{file_name} ({location})" if location else file_name
    return f"{header}\n\n{draft.text}"


class IngestionWorker:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        embedder: Embedder,
        chunker: Chunker,
        settings: IngestionSettings,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self._session_factory = session_factory
        self._embedder = embedder
        self._chunker = chunker
        self._settings = settings
        self._clock = clock

    async def run(self, stop: asyncio.Event) -> None:
        logger.info("Ingestion worker started")
        while not stop.is_set():
            try:
                processed = await self.process_next()
            except Exception:
                # The document keeps its lease and is picked up again once the lease expires.
                logger.exception("Ingestion failed unexpectedly")
                processed = False
            if not processed:
                with suppress(TimeoutError):
                    await asyncio.wait_for(stop.wait(), self._settings.poll_interval_seconds)
        logger.info("Ingestion worker stopped")

    async def process_next(self) -> bool:
        claim = await self._claim_next()
        if claim is None:
            return False

        logger.info("Ingesting document %s (%s)", claim.document_id, claim.file_name)
        try:
            ingested = await self._ingest(claim)
        except DocumentParseError as error:
            await self._fail(claim, str(error))
            return True

        await self._complete(claim, ingested)
        return True

    async def _claim_next(self) -> Claim | None:
        async with self._session_factory() as session:
            while True:
                now = self._clock()
                document = await session.scalar(
                    select(Document)
                    .where(
                        or_(
                            Document.status == DocumentStatus.UPLOADED,
                            and_(
                                Document.status == DocumentStatus.PROCESSING,
                                Document.lease_expires_at < now,
                            ),
                        )
                    )
                    .order_by(Document.created_at)
                    .limit(1)
                    .with_for_update(skip_locked=True)
                )
                if document is None:
                    return None

                if document.has_exhausted_attempts(self._settings.max_attempts):
                    document.mark_failed(f"Gave up after {document.attempts} attempts.")
                    await session.commit()
                    logger.warning(
                        "Document %s failed after %s attempts", document.id, document.attempts
                    )
                    continue

                lease_token = document.start_processing(now, self._settings.lease_seconds)
                content = (
                    await session.execute(
                        select(DocumentFile.content).where(DocumentFile.document_id == document.id)
                    )
                ).scalar_one()
                await session.commit()
                return Claim(
                    document.id,
                    document.collection_id,
                    lease_token,
                    document.file_name,
                    document.format,
                    content,
                )

    async def _ingest(self, claim: Claim) -> IngestedChunks:
        parsed = parser_for(claim.file_format).parse(claim.content)
        drafts = self._chunker.split(parsed.sections)
        if not drafts:
            raise DocumentParseError("The file contains no text that can be searched.")
        embeddings = await self._embedder.embed_documents(
            [embedding_input(claim.file_name, draft) for draft in drafts]
        )
        return IngestedChunks(drafts, embeddings, parsed.page_count)

    async def _complete(self, claim: Claim, ingested: IngestedChunks) -> None:
        async with self._session_factory() as session:
            document = await self._lock(session, claim)
            if document is None:
                return
            try:
                document.mark_ready(claim.lease_token, ingested.page_count, self._clock())
            except LeaseLostError:
                logger.warning("Discarding result for %s: lease was taken over", claim.document_id)
                return

            session.add_all(
                Chunk(
                    id=uuid.uuid4(),
                    document_id=claim.document_id,
                    collection_id=claim.collection_id,
                    ordinal=ordinal,
                    text=draft.text,
                    page_number=draft.location.page_number,
                    heading_path=list(draft.location.heading_path),
                    word_count=draft.word_count,
                    embedding=embedding,
                    embedding_model=self._embedder.model,
                )
                for ordinal, (draft, embedding) in enumerate(
                    zip(ingested.drafts, ingested.embeddings, strict=True)
                )
            )
            if document.replaces_document_id is not None:
                await session.execute(
                    delete(Document).where(Document.id == document.replaces_document_id)
                )
            await session.commit()
            logger.info(
                "Document %s is ready with %s chunks", claim.document_id, len(ingested.drafts)
            )

    async def _fail(self, claim: Claim, reason: str) -> None:
        async with self._session_factory() as session:
            document = await self._lock(session, claim)
            if document is None:
                return
            try:
                document.ensure_lease_held(claim.lease_token)
            except LeaseLostError:
                return
            document.mark_failed(reason)
            await session.commit()
            logger.warning("Document %s failed: %s", claim.document_id, reason)

    async def _lock(self, session: AsyncSession, claim: Claim) -> Document | None:
        document = await session.scalar(
            select(Document).where(Document.id == claim.document_id).with_for_update()
        )
        if document is None:
            logger.info("Document %s was deleted during ingestion", claim.document_id)
        return document
