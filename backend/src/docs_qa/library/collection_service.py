import uuid
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import Select, case, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from docs_qa.errors import NotFoundError
from docs_qa.library.enums import DocumentStatus
from docs_qa.library.errors import DuplicateCollectionNameError
from docs_qa.library.models import Collection, Document


@dataclass(frozen=True)
class CollectionOverview:
    collection: Collection
    document_count: int
    ready_document_count: int


class CollectionService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(self) -> list[CollectionOverview]:
        rows = await self._session.execute(_overview_query().order_by(Collection.name))
        return [CollectionOverview(*row) for row in rows.tuples()]

    async def get_overview(self, collection_id: UUID) -> CollectionOverview:
        row = (
            (await self._session.execute(_overview_query().where(Collection.id == collection_id)))
            .tuples()
            .first()
        )
        if row is None:
            raise NotFoundError("Collection", collection_id)
        return CollectionOverview(*row)

    async def get(self, collection_id: UUID) -> Collection:
        collection = await self._session.get(Collection, collection_id)
        if collection is None:
            raise NotFoundError("Collection", collection_id)
        return collection

    async def find_by_name(self, name: str) -> Collection | None:
        return await self._session.scalar(select(Collection).where(Collection.name == name))

    async def create(self, name: str) -> Collection:
        collection = Collection(id=uuid.uuid4(), name=name)
        self._session.add(collection)
        await self._commit_unique_name(name)
        return collection

    async def rename(self, collection_id: UUID, name: str) -> Collection:
        collection = await self.get(collection_id)
        collection.rename(name)
        await self._commit_unique_name(name)
        return collection

    async def delete(self, collection_id: UUID) -> None:
        await self._session.delete(await self.get(collection_id))
        await self._session.commit()

    async def _commit_unique_name(self, name: str) -> None:
        try:
            await self._session.commit()
        except IntegrityError as error:
            await self._session.rollback()
            raise DuplicateCollectionNameError(name) from error


def _overview_query() -> Select[Collection, int, int]:
    is_ready = case((Document.status == DocumentStatus.READY, 1), else_=0)
    return (
        select(Collection, func.count(Document.id), func.coalesce(func.sum(is_ready), 0))
        .outerjoin(Document, Document.collection_id == Collection.id)
        .group_by(Collection.id)
    )
