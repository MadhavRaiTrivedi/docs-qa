from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class FusedRank:
    chunk_id: UUID
    score: float
    vector_rank: int | None
    keyword_rank: int | None


def reciprocal_rank_fusion(
    vector_ids: Sequence[UUID], keyword_ids: Sequence[UUID], k: int
) -> list[FusedRank]:
    """Merges two rankings by summing 1 / (k + rank) per chunk.

    Only ranks are used, never raw scores, because cosine distance and ts_rank are on
    different scales. A chunk found by both searches beats one found by a single search.
    """
    vector_ranks = {chunk_id: rank for rank, chunk_id in enumerate(vector_ids, start=1)}
    keyword_ranks = {chunk_id: rank for rank, chunk_id in enumerate(keyword_ids, start=1)}

    fused = []
    for chunk_id in vector_ranks.keys() | keyword_ranks.keys():
        vector_rank = vector_ranks.get(chunk_id)
        keyword_rank = keyword_ranks.get(chunk_id)
        score = sum(1 / (k + rank) for rank in (vector_rank, keyword_rank) if rank is not None)
        fused.append(FusedRank(chunk_id, score, vector_rank, keyword_rank))

    return sorted(fused, key=lambda hit: (-hit.score, hit.vector_rank or len(vector_ranks) + 1))
