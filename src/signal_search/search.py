"""Query evaluation and basic relevance ranking."""

from signal_search.text import tokenize

InvertedIndex = dict[str, dict[str, int]]
SearchResult = tuple[str, int]


def search(index: InvertedIndex, query: str) -> list[SearchResult]:
    """Return matching documents ordered by total token frequency."""
    scores: dict[str, int] = {}

    for token in set(tokenize(query)):
        for document_id, frequency in index.get(token, {}).items():
            scores[document_id] = scores.get(document_id, 0) + frequency

    return sorted(scores.items(), key=lambda result: (-result[1], result[0]))

