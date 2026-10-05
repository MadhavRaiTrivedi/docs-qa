from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import StringConstraints

from docs_qa.answering.enums import AnswerOutcome, Rating
from docs_qa.answering.models import AnswerSource, Question, QuestionFeedback
from docs_qa.api_model import ApiModel

QuestionText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=3, max_length=1000)
]
FeedbackComment = Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)]


class QuestionRequest(ApiModel):
    question: QuestionText


class FeedbackRequest(ApiModel):
    rating: Rating
    comment: FeedbackComment | None = None


class FeedbackResponse(ApiModel):
    rating: Rating
    comment: str | None
    updated_at: datetime

    @classmethod
    def from_feedback(cls, feedback: QuestionFeedback) -> "FeedbackResponse":
        return cls(rating=feedback.rating, comment=feedback.comment, updated_at=feedback.updated_at)


class SourceResponse(ApiModel):
    number: int
    chunk_id: UUID
    document_id: UUID
    file_name: str
    page_number: int | None
    heading_path: list[str]
    text: str
    score: float
    similarity: float | None
    is_cited: bool

    @classmethod
    def from_source(cls, source: AnswerSource) -> "SourceResponse":
        return cls(
            number=source.number,
            chunk_id=UUID(source.chunk_id),
            document_id=UUID(source.document_id),
            file_name=source.file_name,
            page_number=source.page_number,
            heading_path=source.heading_path,
            text=source.text,
            score=source.score,
            similarity=source.similarity,
            is_cited=source.is_cited,
        )


class QuestionResponse(ApiModel):
    id: UUID
    collection_id: UUID
    question: str
    answer: str
    outcome: AnswerOutcome
    model: str | None
    sources: list[SourceResponse]
    input_tokens: int | None
    output_tokens: int | None
    cached_input_tokens: int | None
    latency_ms: int
    created_at: datetime
    feedback: FeedbackResponse | None

    @classmethod
    def from_question(
        cls, question: Question, feedback: QuestionFeedback | None = None
    ) -> "QuestionResponse":
        return cls(
            id=question.id,
            collection_id=question.collection_id,
            question=question.text,
            answer=question.answer,
            outcome=question.outcome,
            model=question.model,
            sources=[SourceResponse.from_source(source) for source in question.sources],
            input_tokens=question.input_tokens,
            output_tokens=question.output_tokens,
            cached_input_tokens=question.cached_input_tokens,
            latency_ms=question.latency_ms,
            created_at=question.created_at,
            feedback=FeedbackResponse.from_feedback(feedback) if feedback else None,
        )
