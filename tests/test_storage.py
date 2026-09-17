from signal_search.engine import SearchEngine
from signal_search.storage import SQLiteDocumentStore


def test_sqlite_store_persists_documents_between_engines(tmp_path) -> None:
    database_path = tmp_path / "signal-search.db"
    first_store = SQLiteDocumentStore(database_path)
    first_engine = SearchEngine(store=first_store)
    first_engine.add_documents(
        {
            "doc-1": "Python search engine",
            "doc-2": "Rust systems",
        }
    )
    first_engine.close()

    second_store = SQLiteDocumentStore(database_path)
    second_engine = SearchEngine(store=second_store)

    assert second_engine.documents == {
        "doc-1": "Python search engine",
        "doc-2": "Rust systems",
    }
    assert second_engine.search("python") == [("doc-1", 1)]
    second_engine.close()


def test_sqlite_store_persists_replacements_and_removals(tmp_path) -> None:
    database_path = tmp_path / "signal-search.db"
    first_engine = SearchEngine(store=SQLiteDocumentStore(database_path))
    first_engine.add_document("doc-1", "python")
    first_engine.add_document("doc-1", "rust")
    first_engine.add_document("doc-2", "systems")
    first_engine.remove_document("doc-2")
    first_engine.close()

    second_engine = SearchEngine(store=SQLiteDocumentStore(database_path))

    assert second_engine.documents == {"doc-1": "rust"}
    second_engine.clear()
    second_engine.close()

    final_store = SQLiteDocumentStore(database_path)
    assert final_store.load_documents() == {}
    final_store.close()
