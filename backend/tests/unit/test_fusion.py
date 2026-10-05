import uuid

from docs_qa.search.fusion import reciprocal_rank_fusion

K = 60


def test_chunk_found_by_both_searches_ranks_first() -> None:
    only_vector, both, only_keyword = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()

    fused = reciprocal_rank_fusion([only_vector, both], [both, only_keyword], K)

    assert [hit.chunk_id for hit in fused] == [both, only_vector, only_keyword]


def test_score_is_the_sum_of_reciprocal_ranks() -> None:
    chunk = uuid.uuid4()

    [hit] = reciprocal_rank_fusion([chunk], [chunk], K)

    assert hit.score == 2 / (K + 1)
    assert (hit.vector_rank, hit.keyword_rank) == (1, 1)


def test_equal_scores_prefer_the_vector_result() -> None:
    vector_first, keyword_first = uuid.uuid4(), uuid.uuid4()

    fused = reciprocal_rank_fusion([vector_first], [keyword_first], K)

    assert [hit.chunk_id for hit in fused] == [vector_first, keyword_first]
    assert fused[1].vector_rank is None


def test_empty_rankings_give_no_hits() -> None:
    assert reciprocal_rank_fusion([], [], K) == []
