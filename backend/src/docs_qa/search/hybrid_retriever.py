from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import Text, cast, func, literal_column, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.expression import ColumnClause

from docs_qa.errors import NotFoundError
from docs_qa.ingestion.embedding import Embedder
from docs_qa.library.models import Chunk, ChunkLocation, Collection, Document
from docs_qa.search.fusion import reciprocal_rank_fusion
from docs_qa.settings import RetrievalSettings

# Must match the configuration of the chunks.search_vector column.
_TEXT_SEARCH_CONFIG: ColumnClause[str] = literal_column("'english'")


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: UUID
    document_id: UUID
    file_name: str
    text: str
    location: ChunkLocation
    score: float
    similarity: float | None
    vector_rank: int | None
    keyword_rank: int | None


@dataclass(frozen=True)
class RetrievalResult:
    chunks: list[RetrievedChunk]
    best_similarity: float | None


class HybridRetriever:
    def __init__(
        self, session: AsyncSession, embedder: Embedder, settings: RetrievalSettings
    ) -> None:
        self._session = session
        self._embedder = embedder
        self._settings = settings

    async def retrieve(self, collection_id: UUID, query: str) -> RetrievalResult:
        if await self._session.get(Collection, collection_id) is None:
            raise NotFoundError("Collection", collection_id)

        query_embedding = await self._embedder.embed_query(query)
        similarities = await self._vector_search(collection_id, query_embedding)
        keyword_ids = await self._keyword_search(collection_id, query)

        fused = reciprocal_rank_fusion(list(similarities), keyword_ids, self._settings.rrf_k)
        top = fused[: self._settings.top_k]
        chunks = await self._load([hit.chunk_id for hit in top])

        retrieved = [
            RetrievedChunk(
                chunk_id=hit.chunk_id,
                document_id=chunk.document_id,
                file_name=file_name,
                text=chunk.text,
                location=chunk.location,
                score=hit.score,
                similarity=similarities.get(hit.chunk_id),
                vector_rank=hit.vector_rank,
                keyword_rank=hit.keyword_rank,
            )
            for hit in top
            for chunk, file_name in [chunks[hit.chunk_id]]
        ]
        return RetrievalResult(retrieved, max(similarities.values(), default=None))

    async def _vector_search(
        self, collection_id: UUID, query_embedding: list[float]
    ) -> dict[UUID, float]:
        # Without iterative scan, HNSW returns its first ef_search candidates and the collection
        # filter runs afterwards, so a small collection in a large table gets too few rows.
        await self._session.execute(text("SET LOCAL hnsw.iterative_scan = relaxed_order"))
        distance = Chunk.embedding.cosine_distance(query_embedding)
        rows = await self._session.execute(
            select(Chunk.id, distance)
            .where(
                Chunk.collection_id == collection_id,
                Chunk.embedding_model == self._embedder.model,
            )
            .order_by(distance)
            .limit(self._settings.candidates_per_search)
        )
        # relaxed_order may return rows slightly out of order, so sort again here.
        ordered = sorted(rows, key=lambda row: float(row[1]))
        return {chunk_id: 1 - float(chunk_distance) for chunk_id, chunk_distance in ordered}

    async def _keyword_search(self, collection_id: UUID, query: str) -> list[UUID]:
        # plainto_tsquery joins words with AND, which almost never matches a whole question.
        # Turning it into OR lets ts_rank_cd reward chunks that match more of the words.
        all_words = cast(func.plainto_tsquery(_TEXT_SEARCH_CONFIG, query), Text)
        any_word = func.to_tsquery(_TEXT_SEARCH_CONFIG, func.replace(all_words, " & ", " | "))
        rank = func.ts_rank_cd(Chunk.search_vector, any_word)
        rows = await self._session.scalars(
            select(Chunk.id)
            .where(Chunk.collection_id == collection_id, Chunk.search_vector.op("@@")(any_word))
            .order_by(rank.desc())
            .limit(self._settings.candidates_per_search)
        )
        return list(rows)

    async def _load(self, chunk_ids: list[UUID]) -> dict[UUID, tuple[Chunk, str]]:
        rows = await self._session.execute(
            select(Chunk, Document.file_name)
            .join(Document, Document.id == Chunk.document_id)
            .where(Chunk.id.in_(chunk_ids))
        )
        return {chunk.id: (chunk, file_name) for chunk, file_name in rows.tuples()}
