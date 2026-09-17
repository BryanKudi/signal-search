import pytest

from signal_search.search import bm25_search, search, tfidf_search


def test_search_ranks_documents_by_total_frequency() -> None:
    index = {
        "python": {"a": 2, "b": 1},
        "search": {"a": 1, "c": 3},
    }

    assert search(index, "python search") == [
        ("a", 3),
        ("c", 3),
        ("b", 1),
    ]


def test_search_normalizes_query_text() -> None:
    index = {"python": {"doc-1": 2}}

    assert search(index, "PYTHON!") == [("doc-1", 2)]


def test_search_does_not_double_count_repeated_query_tokens() -> None:
    index = {"python": {"doc-1": 2}}

    assert search(index, "python python") == [("doc-1", 2)]


def test_search_returns_empty_list_when_nothing_matches() -> None:
    assert search({}, "missing") == []


def test_tfidf_search_rewards_rare_query_tokens() -> None:
    index = {
        "common": {"a": 2, "b": 1, "c": 1},
        "rare": {"b": 1},
    }

    results = tfidf_search(index, "common rare", total_documents=3)

    assert [document_id for document_id, _ in results] == ["b", "a", "c"]
    assert results[0][1] == pytest.approx(2.693147)
    assert results[1][1] == pytest.approx(2.0)
    assert results[2][1] == pytest.approx(1.0)


def test_tfidf_search_normalizes_and_deduplicates_query_tokens() -> None:
    index = {"python": {"doc-1": 2}}

    once = tfidf_search(index, "python", total_documents=2)
    repeated = tfidf_search(index, "PYTHON! python", total_documents=2)

    assert repeated == once


def test_tfidf_search_requires_a_positive_document_count() -> None:
    with pytest.raises(ValueError, match="must be positive"):
        tfidf_search({}, "python", total_documents=0)


def test_bm25_normalizes_scores_by_document_length() -> None:
    index = {"python": {"short": 1, "long": 1}}

    results = bm25_search(
        index,
        "python",
        document_lengths={"short": 2, "long": 20},
        total_documents=2,
        average_document_length=11,
    )

    assert [document_id for document_id, _ in results] == ["short", "long"]
    assert results[0][1] > results[1][1]


def test_bm25_rewards_rare_terms() -> None:
    index = {
        "common": {"a": 1, "b": 1, "c": 1},
        "rare": {"b": 1},
    }

    results = bm25_search(
        index,
        "common rare",
        document_lengths={"a": 1, "b": 2, "c": 1},
        total_documents=3,
        average_document_length=4 / 3,
    )

    assert results[0][0] == "b"


@pytest.mark.parametrize(
    ("arguments", "message"),
    [
        ({"total_documents": 0}, "total_documents must be positive"),
        ({"average_document_length": -1}, "cannot be negative"),
        ({"k1": 0}, "k1 must be positive"),
        ({"b": 2}, "b must be between"),
    ],
)
def test_bm25_validates_scoring_parameters(
    arguments: dict[str, int],
    message: str,
) -> None:
    options = {
        "document_lengths": {},
        "total_documents": 1,
        "average_document_length": 0,
        **arguments,
    }

    with pytest.raises(ValueError, match=message):
        bm25_search({}, "python", **options)
