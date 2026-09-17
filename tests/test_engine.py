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


def test_search_engine_removes_document_and_rebuilds_index() -> None:
    engine = SearchEngine()
    engine.add_documents(
        {
            "doc-1": "python search",
            "doc-2": "rust systems",
        }
    )

    removed = engine.remove_document("doc-1")

    assert removed is True
    assert engine.search("python") == []
    assert engine.search("rust") == [("doc-2", 1)]


def test_search_engine_reports_when_document_is_missing() -> None:
    engine = SearchEngine()
    engine.add_document("doc-1", "python search")

    removed = engine.remove_document("missing")

    assert removed is False
    assert engine.search("python") == [("doc-1", 1)]


def test_search_engine_clears_documents_and_index() -> None:
    engine = SearchEngine()
    engine.add_documents(
        {
            "doc-1": "python search",
            "doc-2": "rust systems",
        }
    )

    engine.clear()

    assert engine.documents == {}
    assert engine.index == {}
    assert engine.search("python") == []
    assert engine.tfidf_search("rust") == []


def test_search_engine_runs_bm25_ranking() -> None:
    engine = SearchEngine(
        {
            "short": "python guide",
            "long": "python guide with several additional unrelated words",
        }
    )

    results = engine.bm25_search("python")

    assert [document_id for document_id, _ in results] == ["short", "long"]


def test_search_engine_caches_normalized_queries() -> None:
    engine = SearchEngine({"doc-1": "Python search"})

    engine.tfidf_search("python")
    engine.tfidf_search("PYTHON!")
    metrics = engine.metrics()

    assert metrics.search_count == 2
    assert metrics.cache_hits == 1
    assert metrics.cache_misses == 1
    assert metrics.cache_entries == 1
    assert metrics.cache_hit_rate == 0.5


def test_search_engine_invalidates_cache_after_mutation() -> None:
    engine = SearchEngine({"doc-1": "python"})
    engine.search("python")

    engine.add_document("doc-2", "python")

    assert engine.metrics().cache_entries == 0
    assert engine.search("python") == [("doc-1", 1), ("doc-2", 1)]
    assert engine.metrics().cache_misses == 2


def test_search_engine_evicts_least_recently_used_query() -> None:
    engine = SearchEngine(
        {"doc-1": "python search engine"},
        cache_size=1,
    )

    engine.search("python")
    engine.search("search")
    engine.search("python")

    assert engine.metrics().cache_entries == 1
    assert engine.metrics().cache_hits == 0
    assert engine.metrics().cache_misses == 3


def test_search_engine_rejects_unknown_ranking_algorithm() -> None:
    engine = SearchEngine()

    try:
        engine.rank("python", "pagerank")  # type: ignore[arg-type]
    except ValueError as error:
        assert str(error) == "Unsupported ranking algorithm: pagerank"
    else:
        raise AssertionError("Expected an unsupported ranking error")
