from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from docs_qa.answering.enums import Rating
from docs_qa.answering.models import Question, QuestionFeedback
from docs_qa.errors import NotFoundError


@dataclass(frozen=True)
class RatedQuestion:
    question: Question
    feedback: QuestionFeedback | None


class QuestionService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, question_id: UUID) -> RatedQuestion:
        row = (
            await self._session.execute(
                select(Question, QuestionFeedback)
                .outerjoin(QuestionFeedback, QuestionFeedback.question_id == Question.id)
                .where(Question.id == question_id)
            )
        ).first()
        if row is None:
            raise NotFoundError("Question", question_id)
        return RatedQuestion(*row)

    async def list_recent(self, collection_id: UUID, limit: int) -> list[Question]:
        rows = await self._session.scalars(
            select(Question)
            .where(Question.collection_id == collection_id)
            .order_by(Question.created_at.desc())
            .limit(limit)
        )
        return list(rows)

    async def rate(
        self, question_id: UUID, rating: Rating, comment: str | None
    ) -> QuestionFeedback:
        if await self._session.get(Question, question_id) is None:
            raise NotFoundError("Question", question_id)
        feedback = await self._session.merge(
            QuestionFeedback(question_id=question_id, rating=rating, comment=comment)
        )
        await self._session.commit()
        return feedback
