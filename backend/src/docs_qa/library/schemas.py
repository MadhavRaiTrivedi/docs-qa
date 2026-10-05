from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import StringConstraints

from docs_qa.api_model import ApiModel
from docs_qa.library.collection_service import CollectionOverview
from docs_qa.library.document_service import DocumentOverview
from docs_qa.library.enums import DocumentStatus, FileFormat
from docs_qa.library.models import Document

CollectionName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
]


class CollectionRequest(ApiModel):
    name: CollectionName


class CollectionResponse(ApiModel):
    id: UUID
    name: str
    created_at: datetime
    document_count: int
    ready_document_count: int

    @classmethod
    def from_overview(cls, overview: CollectionOverview) -> "CollectionResponse":
        collection = overview.collection
        return cls(
            id=collection.id,
            name=collection.name,
            created_at=collection.created_at,
            document_count=overview.document_count,
            ready_document_count=overview.ready_document_count,
        )


class DocumentResponse(ApiModel):
    id: UUID
    collection_id: UUID
    file_name: str
    format: FileFormat
    size_bytes: int
    status: DocumentStatus
    failure_reason: str | None
    attempts: int
    page_count: int | None
    chunk_count: int
    replaces_document_id: UUID | None
    created_at: datetime
    ready_at: datetime | None

    @classmethod
    def from_document(cls, document: Document, chunk_count: int = 0) -> "DocumentResponse":
        return cls(
            id=document.id,
            collection_id=document.collection_id,
            file_name=document.file_name,
            format=document.format,
            size_bytes=document.size_bytes,
            status=document.status,
            failure_reason=document.failure_reason,
            attempts=document.attempts,
            page_count=document.page_count,
            chunk_count=chunk_count,
            replaces_document_id=document.replaces_document_id,
            created_at=document.created_at,
            ready_at=document.ready_at,
        )

    @classmethod
    def from_overview(cls, overview: DocumentOverview) -> "DocumentResponse":
        return cls.from_document(overview.document, overview.chunk_count)
