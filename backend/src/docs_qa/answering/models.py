import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from docs_qa.answering.enums import AnswerOutcome, Rating
from docs_qa.database import Base
from docs_qa.search.hybrid_retriever import RetrievedChunk


def _utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True)
class TokenUsage:
    input_tokens: int
    output_tokens: int
    cached_input_tokens: int


@dataclass(frozen=True)
class AnswerSource:
    """A copy of one retrieved chunk as it was when the question was answered.

    Chunks are deleted when their document is replaced, so a question keeps its own copy
    to stay explainable later.
    """

    number: int
    chunk_id: str
    document_id: str
    file_name: str
    page_number: int | None
    heading_path: list[str]
    text: str
    score: float
    similarity: float | None
    vector_rank: int | None
    keyword_rank: int | None
    is_cited: bool

    @classmethod
    def from_retrieved(cls, number: int, chunk: RetrievedChunk, is_cited: bool) -> "AnswerSource":
        return cls(
            number=number,
            chunk_id=str(chunk.chunk_id),
            document_id=str(chunk.document_id),
            file_name=chunk.file_name,
            page_number=chunk.location.page_number,
            heading_path=list(chunk.location.heading_path),
            text=chunk.text,
            score=chunk.score,
            similarity=chunk.similarity,
            vector_rank=chunk.vector_rank,
            keyword_rank=chunk.keyword_rank,
            is_cited=is_cited,
        )


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    collection_id: Mapped[UUID] = mapped_column(ForeignKey("collections.id", ondelete="CASCADE"))
    text: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text)
    outcome: Mapped[AnswerOutcome] = mapped_column(
        Enum(AnswerOutcome, native_enum=False, length=20)
    )
    model: Mapped[str | None] = mapped_column(String(100))
    source_snapshots: Mapped[list[dict[str, Any]]] = mapped_column("sources", JSONB)
    input_tokens: Mapped[int | None]
    output_tokens: Mapped[int | None]
    cached_input_tokens: Mapped[int | None]
    latency_ms: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    @classmethod
    def record(
        cls,
        collection_id: UUID,
        text: str,
        answer: str,
        outcome: AnswerOutcome,
        sources: list[AnswerSource],
        latency_ms: int,
        model: str | None = None,
        usage: TokenUsage | None = None,
    ) -> "Question":
        return cls(
            id=uuid.uuid4(),
            collection_id=collection_id,
            text=text,
            answer=answer,
            outcome=outcome,
            model=model,
            source_snapshots=[asdict(source) for source in sources],
            input_tokens=usage.input_tokens if usage else None,
            output_tokens=usage.output_tokens if usage else None,
            cached_input_tokens=usage.cached_input_tokens if usage else None,
            latency_ms=latency_ms,
        )

    @property
    def sources(self) -> list[AnswerSource]:
        return [AnswerSource(**snapshot) for snapshot in self.source_snapshots]


class QuestionFeedback(Base):
    __tablename__ = "question_feedback"

    question_id: Mapped[UUID] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE"), primary_key=True
    )
    rating: Mapped[Rating] = mapped_column(Enum(Rating, native_enum=False, length=20))
    comment: Mapped[str | None] = mapped_column(Text)
    # Set in Python so the new value is known without reading the row back after an update.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, onupdate=_utc_now
    )
