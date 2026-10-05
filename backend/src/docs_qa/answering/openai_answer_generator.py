from collections.abc import AsyncIterator, Sequence

from openai import AsyncOpenAI
from openai.types.responses import (
    ResponseCompletedEvent,
    ResponseErrorEvent,
    ResponseFailedEvent,
    ResponseIncompleteEvent,
    ResponseTextDeltaEvent,
    ResponseUsage,
)

from docs_qa.answering.answer_generator import GenerationCompleted, GenerationEvent, TextDelta
from docs_qa.answering.errors import AnswerGenerationError
from docs_qa.answering.models import TokenUsage
from docs_qa.answering.prompt import INSTRUCTIONS, render_input
from docs_qa.search.hybrid_retriever import RetrievedChunk
from docs_qa.settings import OpenAISettings


class OpenAIAnswerGenerator:
    def __init__(self, client: AsyncOpenAI, settings: OpenAISettings) -> None:
        self._client = client
        self._settings = settings

    @property
    def model(self) -> str:
        return self._settings.model

    async def stream(
        self, question: str, sources: Sequence[RetrievedChunk]
    ) -> AsyncIterator[GenerationEvent]:
        events = await self._client.responses.create(
            model=self._settings.model,
            instructions=INSTRUCTIONS,
            input=render_input(question, sources),
            max_output_tokens=self._settings.max_output_tokens,
            # Internal documents should not be kept on OpenAI's side for later retrieval.
            store=False,
            stream=True,
        )
        async for event in events:
            match event:
                case ResponseTextDeltaEvent(delta=delta):
                    yield TextDelta(delta)
                case (
                    ResponseCompletedEvent(response=response)
                    | ResponseIncompleteEvent(response=response)
                ):
                    yield GenerationCompleted(_token_usage(response.usage))
                case ResponseFailedEvent(response=response):
                    message = response.error.message if response.error else "unknown error"
                    raise AnswerGenerationError(f"OpenAI could not answer: {message}")
                case ResponseErrorEvent(message=message):
                    raise AnswerGenerationError(f"OpenAI returned an error: {message}")


def _token_usage(usage: ResponseUsage | None) -> TokenUsage:
    if usage is None:
        return TokenUsage(0, 0, 0)
    return TokenUsage(
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        cached_input_tokens=usage.input_tokens_details.cached_tokens,
    )
