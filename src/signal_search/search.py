"""Query evaluation and basic relevance ranking."""

from math import log

from signal_search.text import tokenize

InvertedIndex = dict[str, dict[str, int]]
SearchResult = tuple[str, int]
TFIDFResult = tuple[str, float]


def search(index: InvertedIndex, query: str) -> list[SearchResult]:
    """Return matching documents ordered by total token frequency."""
    scores: dict[str, int] = {}

    for token in set(tokenize(query)):
        for document_id, frequency in index.get(token, {}).items():
            scores[document_id] = scores.get(document_id, 0) + frequency

    return sorted(scores.items(), key=lambda result: (-result[1], result[0]))


def tfidf_search(
    index: InvertedIndex,
    query: str,
    total_documents: int,
) -> list[TFIDFResult]:
    """Rank matching documents with smoothed TF-IDF scores."""
    if total_documents < 1:
        raise ValueError("total_documents must be positive")

    scores: dict[str, float] = {}

    for token in set(tokenize(query)):
        postings = index.get(token, {})
        document_frequency = len(postings)

        if document_frequency == 0:
            continue

        inverse_document_frequency = (
            log((total_documents + 1) / (document_frequency + 1)) + 1
        )

        for document_id, term_frequency in postings.items():
            token_score = term_frequency * inverse_document_frequency
            scores[document_id] = scores.get(document_id, 0.0) + token_score

    return sorted(scores.items(), key=lambda result: (-result[1], result[0]))
