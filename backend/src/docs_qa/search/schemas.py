from typing import Annotated
from uuid import UUID

from pydantic import StringConstraints

from docs_qa.api_model import ApiModel
from docs_qa.search.hybrid_retriever import RetrievalResult, RetrievedChunk

SearchText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=1000)]


class SearchRequest(ApiModel):
    query: SearchText


class SearchHitResponse(ApiModel):
    chunk_id: UUID
    document_id: UUID
    file_name: str
    page_number: int | None
    heading_path: list[str]
    text: str
    score: float
    similarity: float | None
    vector_rank: int | None
    keyword_rank: int | None

    @classmethod
    def from_chunk(cls, chunk: RetrievedChunk) -> "SearchHitResponse":
        return cls(
            chunk_id=chunk.chunk_id,
            document_id=chunk.document_id,
            file_name=chunk.file_name,
            page_number=chunk.location.page_number,
            heading_path=list(chunk.location.heading_path),
            text=chunk.text,
            score=chunk.score,
            similarity=chunk.similarity,
            vector_rank=chunk.vector_rank,
            keyword_rank=chunk.keyword_rank,
        )


class SearchResponse(ApiModel):
    hits: list[SearchHitResponse]
    best_similarity: float | None

    @classmethod
    def from_result(cls, result: RetrievalResult) -> "SearchResponse":
        return cls(
            hits=[SearchHitResponse.from_chunk(chunk) for chunk in result.chunks],
            best_similarity=result.best_similarity,
        )
