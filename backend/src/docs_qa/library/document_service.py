from dataclasses import dataclass
from hashlib import sha256
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from docs_qa.errors import NotFoundError
from docs_qa.library.file_format import detect_file_format
from docs_qa.library.models import Chunk, Collection, Document, DocumentFile


@dataclass(frozen=True)
class DocumentOverview:
    document: Document
    chunk_count: int


@dataclass(frozen=True)
class UploadOutcome:
    document: Document
    is_duplicate: bool


class DocumentService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(self, collection_id: UUID) -> list[DocumentOverview]:
        await self._ensure_collection_exists(collection_id)
        rows = await self._session.execute(
            _overview_query()
            .where(Document.collection_id == collection_id)
            .order_by(Document.created_at.desc())
        )
        return [DocumentOverview(document, count) for document, count in rows.tuples()]

    async def get_overview(self, document_id: UUID) -> DocumentOverview:
        row = (
            (await self._session.execute(_overview_query().where(Document.id == document_id)))
            .tuples()
            .first()
        )
        if row is None:
            raise NotFoundError("Document", document_id)
        return DocumentOverview(*row)

    async def get(self, document_id: UUID) -> Document:
        document = await self._session.get(Document, document_id)
        if document is None:
            raise NotFoundError("Document", document_id)
        return document

    async def upload(self, collection_id: UUID, file_name: str, content: bytes) -> UploadOutcome:
        await self._ensure_collection_exists(collection_id)
        return await self._store(collection_id, file_name, content, replaces_document_id=None)

    async def upload_version(
        self, document_id: UUID, file_name: str, content: bytes
    ) -> UploadOutcome:
        current = await self.get(document_id)
        return await self._store(current.collection_id, file_name, content, current.id)

    async def retry(self, document_id: UUID) -> Document:
        document = await self.get(document_id)
        document.retry()
        await self._session.commit()
        return document

    async def delete(self, document_id: UUID) -> None:
        await self._session.delete(await self.get(document_id))
        await self._session.commit()

    async def _store(
        self,
        collection_id: UUID,
        file_name: str,
        content: bytes,
        replaces_document_id: UUID | None,
    ) -> UploadOutcome:
        existing = await self._find_by_content(collection_id, content)
        if existing is not None:
            return UploadOutcome(existing, is_duplicate=True)

        file_format = detect_file_format(file_name, content)
        document = Document.upload(
            collection_id, file_name, file_format, content, replaces_document_id
        )
        self._session.add(document)
        self._session.add(DocumentFile(document_id=document.id, content=content))
        try:
            await self._session.commit()
        except IntegrityError:
            # Two uploads of the same file raced past the lookup; the unique index kept one.
            await self._session.rollback()
            winner = await self._find_by_content(collection_id, content)
            if winner is None:
                raise
            return UploadOutcome(winner, is_duplicate=True)
        return UploadOutcome(document, is_duplicate=False)

    async def _ensure_collection_exists(self, collection_id: UUID) -> None:
        if await self._session.get(Collection, collection_id) is None:
            raise NotFoundError("Collection", collection_id)

    async def _find_by_content(self, collection_id: UUID, content: bytes) -> Document | None:
        return await self._session.scalar(
            select(Document).where(
                Document.collection_id == collection_id,
                Document.content_sha256 == sha256(content).hexdigest(),
            )
        )


def _overview_query() -> Select[Document, int]:
    return (
        select(Document, func.count(Chunk.id))
        .outerjoin(Chunk, Chunk.document_id == Document.id)
        .group_by(Document.id)
    )
