import re

_CITATION = re.compile(r"\[(\d+(?:\s*,\s*\d+)*)\]")


def cited_source_numbers(answer: str, source_count: int) -> list[int]:
    """Returns the source numbers cited as [n] or [n, m], in order of first appearance.

    Numbers outside 1..source_count are ignored: the model invented them.
    """
    cited: list[int] = []
    for match in _CITATION.finditer(answer):
        for number in (int(part) for part in match.group(1).split(",")):
            if 1 <= number <= source_count and number not in cited:
                cited.append(number)
    return cited
