from signal_search.index import (
    add_document_to_index,
    build_inverted_index,
    remove_document_from_index,
)


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


def test_index_can_be_updated_incrementally() -> None:
    index = build_inverted_index({"doc-1": "python search"})

    add_document_to_index(index, "doc-2", "python systems")
    remove_document_from_index(index, "doc-1")

    assert index == {
        "python": {"doc-2": 1},
        "systems": {"doc-2": 1},
    }
