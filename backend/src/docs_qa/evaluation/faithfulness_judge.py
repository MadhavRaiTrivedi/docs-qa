from collections.abc import Sequence

from openai import AsyncOpenAI
from pydantic import BaseModel

from docs_qa.answering.errors import AnswerGenerationError
from docs_qa.answering.prompt import render_input
from docs_qa.search.hybrid_retriever import RetrievedChunk

JUDGE_INSTRUCTIONS = """\
You check answers produced by a question-answering system over internal documents.
Given the numbered sources, the question and the answer, list every claim in the answer that
the sources do not support. Citations like [2] say which source a claim relies on; a claim
cited to a source that does not support it is unsupported. An answer saying the documents do
not cover the question is faithful when the sources indeed do not answer it.
"""


class FaithfulnessVerdict(BaseModel):
    unsupported_claims: list[str]
    is_faithful: bool


class FaithfulnessJudge:
    def __init__(self, client: AsyncOpenAI, model: str) -> None:
        self._client = client
        self._model = model

    async def judge(
        self, question: str, answer: str, sources: Sequence[RetrievedChunk]
    ) -> FaithfulnessVerdict:
        response = await self._client.responses.parse(
            model=self._model,
            instructions=JUDGE_INSTRUCTIONS,
            input=f"{render_input(question, sources)}\n\nAnswer to check:\n{answer}",
            text_format=FaithfulnessVerdict,
            store=False,
        )
        if response.output_parsed is None:
            raise AnswerGenerationError("The judge returned no verdict.")
        return response.output_parsed
