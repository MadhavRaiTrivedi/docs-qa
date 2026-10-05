import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from hashlib import sha256
from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    ARRAY,
    Computed,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column

from docs_qa.database import Base
from docs_qa.library.enums import DocumentStatus, FileFormat
from docs_qa.library.errors import InvalidDocumentTransitionError, LeaseLostError

# Fixed by the embedding model (text-embedding-3-small) and baked into the migration.
# A model with another size needs a new migration and a full re-ingestion.
EMBEDDING_DIMENSIONS = 1536

_ALLOWED_TRANSITIONS: dict[DocumentStatus, frozenset[DocumentStatus]] = {
    DocumentStatus.UPLOADED: frozenset({DocumentStatus.PROCESSING}),
    DocumentStatus.PROCESSING: frozenset(
        {DocumentStatus.PROCESSING, DocumentStatus.READY, DocumentStatus.FAILED}
    ),
    DocumentStatus.READY: frozenset(),
    DocumentStatus.FAILED: frozenset({DocumentStatus.UPLOADED}),
}


class Collection(Base):
    __tablename__ = "collections"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def rename(self, name: str) -> None:
        self.name = name


@dataclass(frozen=True)
class ChunkLocation:
    page_number: int | None = None
    heading_path: tuple[str, ...] = ()

    def describe(self) -> str:
        parts = []
        if self.page_number is not None:
            parts.append(f"page {self.page_number}")
        if self.heading_path:
            parts.append(" > ".join(self.heading_path))
        return ", ".join(parts)


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    document_id: Mapped[UUID] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    # Copied from the document so retrieval can filter by collection without a join.
    collection_id: Mapped[UUID] = mapped_column(ForeignKey("collections.id", ondelete="CASCADE"))
    ordinal: Mapped[int]
    text: Mapped[str] = mapped_column(Text)
    page_number: Mapped[int | None]
    heading_path: Mapped[list[str]] = mapped_column(ARRAY(Text))
    word_count: Mapped[int]
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIMENSIONS))
    embedding_model: Mapped[str] = mapped_column(String(100))
    search_vector: Mapped[str] = mapped_column(
        TSVECTOR, Computed("to_tsvector('english', text)", persisted=True)
    )

    __table_args__ = (Index("ix_chunks_collection_id", "collection_id"),)

    @property
    def location(self) -> ChunkLocation:
        return ChunkLocation(self.page_number, tuple(self.heading_path))


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    collection_id: Mapped[UUID] = mapped_column(ForeignKey("collections.id", ondelete="CASCADE"))
    file_name: Mapped[str] = mapped_column(String(255))
    format: Mapped[FileFormat] = mapped_column(Enum(FileFormat, native_enum=False, length=20))
    size_bytes: Mapped[int]
    content_sha256: Mapped[str] = mapped_column(String(64))
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, native_enum=False, length=20)
    )
    failure_reason: Mapped[str | None] = mapped_column(Text)
    attempts: Mapped[int] = mapped_column(default=0)
    lease_token: Mapped[UUID | None]
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    page_count: Mapped[int | None]
    replaces_document_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ready_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint("collection_id", "content_sha256", name="uq_documents_collection_content"),
        Index("ix_documents_status_created_at", "status", "created_at"),
    )

    @classmethod
    def upload(
        cls,
        collection_id: UUID,
        file_name: str,
        file_format: FileFormat,
        content: bytes,
        replaces_document_id: UUID | None = None,
    ) -> "Document":
        return cls(
            id=uuid.uuid4(),
            collection_id=collection_id,
            file_name=file_name,
            format=file_format,
            size_bytes=len(content),
            content_sha256=sha256(content).hexdigest(),
            status=DocumentStatus.UPLOADED,
            attempts=0,
            replaces_document_id=replaces_document_id,
        )

    def start_processing(self, now: datetime, lease_seconds: int) -> UUID:
        self._transition_to(DocumentStatus.PROCESSING)
        self.attempts += 1
        self.lease_token = uuid.uuid4()
        self.lease_expires_at = now + timedelta(seconds=lease_seconds)
        return self.lease_token

    def has_exhausted_attempts(self, max_attempts: int) -> bool:
        return self.attempts >= max_attempts

    def ensure_lease_held(self, lease_token: UUID) -> None:
        if self.lease_token != lease_token:
            raise LeaseLostError(self.id)

    def mark_ready(self, lease_token: UUID, page_count: int | None, now: datetime) -> None:
        self.ensure_lease_held(lease_token)
        self._transition_to(DocumentStatus.READY)
        self.page_count = page_count
        self.ready_at = now
        self._release_lease()

    def mark_failed(self, reason: str) -> None:
        self._transition_to(DocumentStatus.FAILED)
        self.failure_reason = reason
        self._release_lease()

    def retry(self) -> None:
        self._transition_to(DocumentStatus.UPLOADED)
        self.attempts = 0
        self.failure_reason = None

    def _release_lease(self) -> None:
        self.lease_token = None
        self.lease_expires_at = None

    def _transition_to(self, target: DocumentStatus) -> None:
        if target not in _ALLOWED_TRANSITIONS[self.status]:
            raise InvalidDocumentTransitionError(self.id, self.status, target)
        self.status = target


class DocumentFile(Base):
    """The uploaded bytes, kept apart from `documents` so listing documents never loads them."""

    __tablename__ = "document_files"

    document_id: Mapped[UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True
    )
    content: Mapped[bytes] = mapped_column(LargeBinary)
