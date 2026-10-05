from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from typing import Protocol

from docs_qa.answering.models import TokenUsage
from docs_qa.search.hybrid_retriever import RetrievedChunk


@dataclass(frozen=True)
class TextDelta:
    text: str


@dataclass(frozen=True)
class GenerationCompleted:
    usage: TokenUsage


type GenerationEvent = TextDelta | GenerationCompleted


class AnswerGenerator(Protocol):
    @property
    def model(self) -> str: ...

    def stream(
        self, question: str, sources: Sequence[RetrievedChunk]
    ) -> AsyncIterator[GenerationEvent]: ...
