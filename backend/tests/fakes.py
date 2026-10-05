import hashlib
import math
import re
from collections.abc import AsyncIterator, Sequence

from docs_qa.answering.answer_generator import GenerationCompleted, GenerationEvent, TextDelta
from docs_qa.answering.models import TokenUsage
from docs_qa.library.models import EMBEDDING_DIMENSIONS
from docs_qa.search.hybrid_retriever import RetrievedChunk

_WORD = re.compile(r"[a-z]+")


class HashingEmbedder:
    """Bag-of-words vectors via the hashing trick: texts sharing words get similar vectors,
    which is enough to test retrieval without running a real model."""

    model = "test-hashing-embedder"

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    async def embed_query(self, text: str) -> list[float]:
        return self._embed(text)

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * EMBEDDING_DIMENSIONS
        for word in _WORD.findall(text.lower()):
            digest = hashlib.sha256(word.encode()).digest()
            vector[int.from_bytes(digest[:4]) % EMBEDDING_DIMENSIONS] += 1.0
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]


class ScriptedAnswerGenerator:
    model = "test-scripted-model"

    def __init__(self, answer: str) -> None:
        self.answer = answer
        self.calls: list[tuple[str, list[RetrievedChunk]]] = []

    async def stream(
        self, question: str, sources: Sequence[RetrievedChunk]
    ) -> AsyncIterator[GenerationEvent]:
        self.calls.append((question, list(sources)))
        for word in self.answer.split(" "):
            yield TextDelta(word + " ")
        yield GenerationCompleted(
            TokenUsage(input_tokens=100, output_tokens=20, cached_input_tokens=0)
        )
