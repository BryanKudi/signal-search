"""Query evaluation and basic relevance ranking."""

from math import log

from signal_search.text import tokenize

InvertedIndex = dict[str, dict[str, int]]
SearchResult = tuple[str, int]
TFIDFResult = tuple[str, float]
BM25Result = tuple[str, float]


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


def bm25_search(
    index: InvertedIndex,
    query: str,
    document_lengths: dict[str, int],
    total_documents: int,
    average_document_length: float,
    *,
    k1: float = 1.5,
    b: float = 0.75,
) -> list[BM25Result]:
    """Rank matching documents with BM25 relevance scoring."""
    if total_documents < 1:
        raise ValueError("total_documents must be positive")
    if average_document_length < 0:
        raise ValueError("average_document_length cannot be negative")
    if k1 <= 0:
        raise ValueError("k1 must be positive")
    if not 0 <= b <= 1:
        raise ValueError("b must be between 0 and 1")

    scores: dict[str, float] = {}

    for token in set(tokenize(query)):
        postings = index.get(token, {})
        document_frequency = len(postings)

        if document_frequency == 0:
            continue

        inverse_document_frequency = log(
            1 + (total_documents - document_frequency + 0.5)
            / (document_frequency + 0.5)
        )

        for document_id, term_frequency in postings.items():
            document_length = document_lengths.get(document_id, 0)
            if average_document_length == 0:
                length_normalization = 1.0
            else:
                length_normalization = 1 - b + b * (
                    document_length / average_document_length
                )

            denominator = term_frequency + k1 * length_normalization
            token_score = inverse_document_frequency * (
                term_frequency * (k1 + 1) / denominator
            )
            scores[document_id] = scores.get(document_id, 0.0) + token_score

    return sorted(scores.items(), key=lambda result: (-result[1], result[0]))
