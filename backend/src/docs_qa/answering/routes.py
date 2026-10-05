import json
import logging
from collections.abc import AsyncIterator
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from openai import OpenAIError

from docs_qa.answering.errors import AnswerGenerationError
from docs_qa.answering.question_answerer import (
    AnswerCompleted,
    AnswerDelta,
    PreparedQuestion,
    QuestionAnswerer,
    SourcesFound,
)
from docs_qa.answering.question_service import QuestionService
from docs_qa.answering.schemas import (
    FeedbackRequest,
    FeedbackResponse,
    QuestionRequest,
    QuestionResponse,
    SourceResponse,
)
from docs_qa.auth.api_key import RequireReader
from docs_qa.dependencies import get_question_answerer, get_question_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["questions"], dependencies=[RequireReader])

Answerer = Annotated[QuestionAnswerer, Depends(get_question_answerer)]
Questions = Annotated[QuestionService, Depends(get_question_service)]

MAX_RECENT_QUESTIONS = 50
_GENERATION_FAILED = "The language model did not return an answer. Try again in a moment."


@router.post("/collections/{collection_id}/questions")
async def ask(
    collection_id: UUID, request: QuestionRequest, answerer: Answerer
) -> QuestionResponse:
    prepared = await answerer.prepare(collection_id, request.question)
    async for event in answerer.answer(prepared):
        if isinstance(event, AnswerCompleted):
            return QuestionResponse.from_question(event.question)
    raise AssertionError("The answer stream ended without a completed answer.")


@router.post(
    "/collections/{collection_id}/questions/stream",
    response_class=StreamingResponse,
    responses={200: {"content": {"text/event-stream": {}}}},
)
async def ask_streaming(
    collection_id: UUID, request: QuestionRequest, answerer: Answerer
) -> StreamingResponse:
    prepared = await answerer.prepare(collection_id, request.question)
    return StreamingResponse(
        _server_sent_events(answerer, prepared),
        media_type="text/event-stream",
        # Stops nginx from buffering the stream, which would deliver the answer all at once.
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/collections/{collection_id}/questions")
async def list_recent_questions(
    collection_id: UUID,
    questions: Questions,
    limit: Annotated[int, Query(ge=1, le=MAX_RECENT_QUESTIONS)] = 20,
) -> list[QuestionResponse]:
    return [
        QuestionResponse.from_question(q) for q in await questions.list_recent(collection_id, limit)
    ]


@router.get("/questions/{question_id}")
async def get_question(question_id: UUID, questions: Questions) -> QuestionResponse:
    rated = await questions.get(question_id)
    return QuestionResponse.from_question(rated.question, rated.feedback)


@router.put("/questions/{question_id}/feedback")
async def rate_answer(
    question_id: UUID, request: FeedbackRequest, questions: Questions
) -> FeedbackResponse:
    feedback = await questions.rate(question_id, request.rating, request.comment)
    return FeedbackResponse.from_feedback(feedback)


async def _server_sent_events(
    answerer: QuestionAnswerer, prepared: PreparedQuestion
) -> AsyncIterator[str]:
    try:
        async for event in answerer.answer(prepared):
            match event:
                case SourcesFound(sources=sources):
                    yield _event(
                        "sources",
                        [
                            SourceResponse.from_source(s).model_dump(mode="json", by_alias=True)
                            for s in sources
                        ],
                    )
                case AnswerDelta(text=text):
                    yield _event("delta", {"text": text})
                case AnswerCompleted(question=question):
                    yield _event(
                        "done",
                        QuestionResponse.from_question(question).model_dump(
                            mode="json", by_alias=True
                        ),
                    )
    except (AnswerGenerationError, OpenAIError):
        # Headers are already sent, so the failure goes to the client as an event, not a status.
        logger.exception("Answer generation failed")
        yield _event("error", {"title": "Answer generation failed", "detail": _GENERATION_FAILED})


def _event(name: str, payload: Any) -> str:
    return f"event: {name}\ndata: {json.dumps(payload)}\n\n"
