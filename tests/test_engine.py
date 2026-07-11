from signal_search.engine import SearchEngine


def test_search_engine_adds_documents_and_runs_basic_search() -> None:
    engine = SearchEngine()

    engine.add_documents(
        {
            "doc-1": "Python search search",
            "doc-2": "Python engine",
        }
    )

    assert engine.search("search python") == [
        ("doc-1", 3),
        ("doc-2", 1),
    ]


def test_search_engine_runs_tfidf_with_document_count() -> None:
    engine = SearchEngine()
    engine.add_documents(
        {
            "doc-1": "common common",
            "doc-2": "common rare",
            "doc-3": "common",
        }
    )

    results = engine.tfidf_search("common rare")

    assert [document_id for document_id, _ in results] == [
        "doc-2",
        "doc-1",
        "doc-3",
    ]


def test_search_engine_returns_empty_results_before_documents_are_added() -> None:
    engine = SearchEngine()

    assert engine.search("python") == []
    assert engine.tfidf_search("python") == []


def test_search_engine_rebuilds_index_when_document_is_replaced() -> None:
    engine = SearchEngine()

    engine.add_document("doc-1", "python search")
    engine.add_document("doc-1", "rust systems")

    assert engine.search("python") == []
    assert engine.search("rust") == [("doc-1", 1)]
