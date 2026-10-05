"""Scores retrieval, and optionally answers, against a set of questions with known sources.

python -m docs_qa.evaluation <dataset.jsonl> --collection <name> [--answers]
"""

import argparse
import asyncio
import sys
from pathlib import Path

import httpx
from openai import AsyncOpenAI

from docs_qa.answering.answer_generator import TextDelta
from docs_qa.answering.citations import cited_source_numbers
from docs_qa.answering.openai_answer_generator import OpenAIAnswerGenerator
from docs_qa.answering.question_answerer import NOT_IN_DOCUMENTS_ANSWER, is_covered
from docs_qa.database import create_engine, create_session_factory
from docs_qa.evaluation.dataset import EvaluationCase, load_cases
from docs_qa.evaluation.faithfulness_judge import FaithfulnessJudge
from docs_qa.evaluation.retrieval_metrics import first_relevant_rank, summarize
from docs_qa.ingestion.embedding import OllamaEmbedder
from docs_qa.library.collection_service import CollectionService
from docs_qa.search.hybrid_retriever import HybridRetriever, RetrievalResult
from docs_qa.settings import Settings, get_settings


async def evaluate(dataset: Path, collection_name: str, with_answers: bool) -> None:
    settings = get_settings()
    if with_answers and settings.openai.api_key is None:
        sys.exit("--answers needs OPENAI_API_KEY.")
    cases = load_cases(dataset)
    engine = create_engine(settings.database.url)

    async with create_session_factory(engine)() as session, httpx.AsyncClient() as http_client:
        collection = await CollectionService(session).find_by_name(collection_name)
        if collection is None:
            sys.exit(f"No collection named '{collection_name}'.")
        embedder = OllamaEmbedder(http_client, settings.embedding)
        retriever = HybridRetriever(session, embedder, settings.retrieval)
        results = [await retriever.retrieve(collection.id, case.question) for case in cases]

    await engine.dispose()
    _report_retrieval(cases, results, settings.retrieval.top_k)
    if with_answers:
        await _report_answers(cases, results, settings)


def _report_retrieval(
    cases: list[EvaluationCase], results: list[RetrievalResult], top_k: int
) -> None:
    ranks = [
        first_relevant_rank(case, result.chunks)
        for case, result in zip(cases, results, strict=True)
    ]
    for case, rank in zip(cases, ranks, strict=True):
        if rank is None:
            print(f"MISS  {case.question}")
    report = summarize(ranks)
    print(f"\nRetrieval over {report.case_count} questions")
    print(f"  hit rate@{top_k}: {report.hit_rate:.2f}")
    print(f"  MRR:          {report.mean_reciprocal_rank:.2f}")


async def _report_answers(
    cases: list[EvaluationCase], results: list[RetrievalResult], settings: Settings
) -> None:
    assert settings.openai.api_key is not None
    client = AsyncOpenAI(api_key=settings.openai.api_key.get_secret_value())
    generator = OpenAIAnswerGenerator(client, settings.openai)
    judge = FaithfulnessJudge(client, settings.openai.model)

    cited_count = 0
    faithful_count = 0
    for case, result in zip(cases, results, strict=True):
        if is_covered(result, settings.retrieval.min_similarity):
            answer = "".join(
                [
                    event.text
                    async for event in generator.stream(case.question, result.chunks)
                    if isinstance(event, TextDelta)
                ]
            )
        else:
            answer = NOT_IN_DOCUMENTS_ANSWER
        cited_count += bool(cited_source_numbers(answer, len(result.chunks)))
        verdict = await judge.judge(case.question, answer, result.chunks)
        faithful_count += verdict.is_faithful
        for claim in verdict.unsupported_claims:
            print(f"UNSUPPORTED  {case.question}\n  {claim}")

    print(f"\nAnswers over {len(cases)} questions (judged by {settings.openai.model})")
    print(f"  with citations: {cited_count / len(cases):.2f}")
    print(f"  faithful:       {faithful_count / len(cases):.2f}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--collection", required=True)
    parser.add_argument("--answers", action="store_true", help="also generate and judge answers")
    arguments = parser.parse_args()
    asyncio.run(evaluate(arguments.dataset, arguments.collection, arguments.answers))


if __name__ == "__main__":
    main()
