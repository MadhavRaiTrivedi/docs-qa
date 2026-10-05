from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from docs_qa.library.models import Chunk


class EmbeddingModelMismatchError(Exception):
    def __init__(self, configured: str, stored: list[str]) -> None:
        super().__init__(
            f"Chunks were embedded with {', '.join(stored)}, but the configured model is "
            f"{configured}. Vectors from different models cannot be compared; delete and "
            "re-upload the documents, or switch the model back."
        )


async def ensure_embedding_model_matches(
    session_factory: async_sessionmaker[AsyncSession], configured: str
) -> None:
    async with session_factory() as session:
        stored = list(
            await session.scalars(
                select(Chunk.embedding_model).where(Chunk.embedding_model != configured).distinct()
            )
        )
    if stored:
        raise EmbeddingModelMismatchError(configured, stored)
