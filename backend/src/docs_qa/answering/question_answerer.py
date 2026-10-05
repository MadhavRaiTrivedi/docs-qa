import time
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from docs_qa.answering.answer_generator import AnswerGenerator, GenerationCompleted, TextDelta
from docs_qa.answering.citations import cited_source_numbers
from docs_qa.answering.enums import AnswerOutcome
from docs_qa.answering.models import AnswerSource, Question, TokenUsage
from docs_qa.search.hybrid_retriever import HybridRetriever, RetrievalResult
from docs_qa.settings import RetrievalSettings

NOT_IN_DOCUMENTS_ANSWER = "The documents in this collection do not cover this question."
MILLISECONDS_PER_SECOND = 1000


def is_covered(retrieval: RetrievalResult, min_similarity: float) -> bool:
    """Whether any chunk is close enough to the question to be worth asking the model."""
    return retrieval.best_similarity is not None and retrieval.best_similarity >= min_similarity


@dataclass(frozen=True)
class PreparedQuestion:
    collection_id: UUID
    text: str
    retrieval: RetrievalResult
    started_at: float


@dataclass(frozen=True)
class SourcesFound:
    sources: list[AnswerSource]


@dataclass(frozen=True)
class AnswerDelta:
    text: str


@dataclass(frozen=True)
class AnswerCompleted:
    question: Question


type AnswerEvent = SourcesFound | AnswerDelta | AnswerCompleted


class QuestionAnswerer:
    """Retrieves sources for a question, streams an answer from them, and records the result.

    `prepare` runs before any response is sent, so a missing collection still becomes a 404
    instead of an error in the middle of a stream.
    """

    def __init__(
        self,
        session: AsyncSession,
        retriever: HybridRetriever,
        generator: AnswerGenerator,
        settings: RetrievalSettings,
        timer: Callable[[], float] = time.perf_counter,
    ) -> None:
        self._session = session
        self._retriever = retriever
        self._generator = generator
        self._settings = settings
        self._timer = timer

    async def prepare(self, collection_id: UUID, text: str) -> PreparedQuestion:
        started_at = self._timer()
        retrieval = await self._retriever.retrieve(collection_id, text)
        return PreparedQuestion(collection_id, text, retrieval, started_at)

    async def answer(self, prepared: PreparedQuestion) -> AsyncIterator[AnswerEvent]:
        chunks = prepared.retrieval.chunks
        uncited = [AnswerSource.from_retrieved(n, c, False) for n, c in enumerate(chunks, 1)]
        yield SourcesFound(uncited)

        if not is_covered(prepared.retrieval, self._settings.min_similarity):
            yield AnswerCompleted(
                await self._save(
                    prepared, NOT_IN_DOCUMENTS_ANSWER, AnswerOutcome.NOT_IN_DOCUMENTS, uncited
                )
            )
            return

        parts: list[str] = []
        usage = TokenUsage(0, 0, 0)
        async for event in self._generator.stream(prepared.text, chunks):
            match event:
                case TextDelta(text=text):
                    parts.append(text)
                    yield AnswerDelta(text)
                case GenerationCompleted(usage=completed_usage):
                    usage = completed_usage

        answer = "".join(parts)
        cited = set(cited_source_numbers(answer, len(chunks)))
        sources = [AnswerSource.from_retrieved(n, c, n in cited) for n, c in enumerate(chunks, 1)]
        outcome = AnswerOutcome.ANSWERED if cited else AnswerOutcome.UNSUPPORTED
        yield AnswerCompleted(await self._save(prepared, answer, outcome, sources, usage))

    async def _save(
        self,
        prepared: PreparedQuestion,
        answer: str,
        outcome: AnswerOutcome,
        sources: list[AnswerSource],
        usage: TokenUsage | None = None,
    ) -> Question:
        elapsed_seconds = self._timer() - prepared.started_at
        question = Question.record(
            collection_id=prepared.collection_id,
            text=prepared.text,
            answer=answer,
            outcome=outcome,
            sources=sources,
            latency_ms=round(elapsed_seconds * MILLISECONDS_PER_SECOND),
            model=self._generator.model if usage else None,
            usage=usage,
        )
        self._session.add(question)
        await self._session.commit()
        return question
