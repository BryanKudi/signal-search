from signal_search.search import search


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

