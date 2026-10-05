import uuid

from docs_qa.evaluation.dataset import EvaluationCase
from docs_qa.evaluation.retrieval_metrics import first_relevant_rank, summarize
from docs_qa.library.models import ChunkLocation
from docs_qa.search.hybrid_retriever import RetrievedChunk

CASE = EvaluationCase(
    question="How many sick days?",
    expected_document="leave.md",
    expected_passage="twelve   days of sick leave",
)


def chunk(file_name: str, text: str) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        file_name=file_name,
        text=text,
        location=ChunkLocation(),
        score=0.0,
        similarity=None,
        vector_rank=None,
        keyword_rank=None,
    )


def test_rank_of_first_chunk_with_the_passage_ignoring_case_and_spacing() -> None:
    chunks = [
        chunk("expenses.md", "Twelve days of sick leave"),
        chunk("leave.md", "Annual leave is 20 days."),
        chunk("leave.md", "Staff get Twelve days\nof sick leave."),
    ]

    assert first_relevant_rank(CASE, chunks) == 3


def test_no_rank_when_the_passage_is_missing() -> None:
    assert first_relevant_rank(CASE, [chunk("leave.md", "Annual leave.")]) is None


def test_summary_counts_misses_as_zero() -> None:
    report = summarize([1, 2, None, None])

    assert report.hit_rate == 0.5
    assert report.mean_reciprocal_rank == (1 + 0.5) / 4
