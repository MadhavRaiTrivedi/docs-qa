import pytest

from docs_qa.answering.citations import cited_source_numbers


@pytest.mark.parametrize(
    ("answer", "expected"),
    [
        ("Twelve days [2]. Paid [1][2].", [2, 1]),
        ("Twelve days [1, 3].", [1, 3]),
        ("No citation here.", []),
        ("Made up [7] and [0].", []),
        ("See [link](http://x) and [2].", [2]),
    ],
)
def test_cited_source_numbers(answer: str, expected: list[int]) -> None:
    assert cited_source_numbers(answer, source_count=3) == expected
