from signal_search.index import build_inverted_index


def test_build_inverted_index_maps_tokens_to_documents() -> None:
    documents = {
        "a": "search search engine",
        "b": "fast engine",
    }

    index = build_inverted_index(documents)

    assert index == {
        "search": {"a": 2},
        "engine": {"a": 1, "b": 1},
        "fast": {"b": 1},
    }


def test_build_inverted_index_accepts_no_documents() -> None:
    assert build_inverted_index({}) == {}


def test_build_inverted_index_normalizes_document_text() -> None:
    documents = {"doc-1": "Python, PYTHON!"}

    assert build_inverted_index(documents) == {
        "python": {"doc-1": 2},
    }

