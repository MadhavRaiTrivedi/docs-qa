from collections.abc import Sequence
from dataclasses import dataclass

from docs_qa.evaluation.dataset import EvaluationCase
from docs_qa.search.hybrid_retriever import RetrievedChunk


@dataclass(frozen=True)
class RetrievalReport:
    case_count: int
    hit_rate: float
    mean_reciprocal_rank: float


def first_relevant_rank(case: EvaluationCase, chunks: Sequence[RetrievedChunk]) -> int | None:
    """Rank (1-based) of the first chunk from the expected document that contains the passage."""
    passage = _normalize(case.expected_passage)
    for rank, chunk in enumerate(chunks, start=1):
        if chunk.file_name == case.expected_document and passage in _normalize(chunk.text):
            return rank
    return None


def summarize(ranks: Sequence[int | None]) -> RetrievalReport:
    if not ranks:
        return RetrievalReport(0, 0.0, 0.0)
    hits = [rank for rank in ranks if rank is not None]
    return RetrievalReport(
        case_count=len(ranks),
        hit_rate=len(hits) / len(ranks),
        mean_reciprocal_rank=sum(1 / rank for rank in hits) / len(ranks),
    )


def _normalize(text: str) -> str:
    return " ".join(text.lower().split())
