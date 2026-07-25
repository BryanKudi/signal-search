from fastapi.testclient import TestClient

from signal_search.api import create_app


def test_root_endpoint_describes_api() -> None:
    client = TestClient(create_app())

    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "name": "Signal Search",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
    }


def test_health_endpoint_reports_ok() -> None:
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_api_adds_document_and_searches_with_tfidf() -> None:
    client = TestClient(create_app())

    add_response = client.post(
        "/documents",
        json={
            "document_id": "doc-1",
            "text": "Python search engine",
        },
    )
    search_response = client.post(
        "/search",
        json={"query": "python"},
    )

    assert add_response.status_code == 201
    assert add_response.json() == {
        "document_id": "doc-1",
        "document_count": 1,
    }
    assert search_response.status_code == 200
    assert search_response.json() == {
        "query": "python",
        "results": [
            {
                "document_id": "doc-1",
                "score": 1.0,
            }
        ],
    }


def test_api_counts_documents() -> None:
    client = TestClient(create_app())
    client.post(
        "/documents",
        json={
            "document_id": "doc-1",
            "text": "Python search engine",
        },
    )
    client.post(
        "/documents",
        json={
            "document_id": "doc-2",
            "text": "Rust systems",
        },
    )

    response = client.get("/documents/count")

    assert response.status_code == 200
    assert response.json() == {"document_count": 2}


def test_api_can_use_frequency_ranking() -> None:
    client = TestClient(create_app())
    client.post(
        "/documents",
        json={
            "document_id": "doc-1",
            "text": "Python python search",
        },
    )

    response = client.post(
        "/search",
        json={
            "query": "python",
            "use_tfidf": False,
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "query": "python",
        "results": [
            {
                "document_id": "doc-1",
                "score": 2.0,
            }
        ],
    }


def test_api_removes_document() -> None:
    client = TestClient(create_app())
    client.post(
        "/documents",
        json={
            "document_id": "doc-1",
            "text": "Python search engine",
        },
    )

    delete_response = client.delete("/documents/doc-1")
    search_response = client.post("/search", json={"query": "python"})

    assert delete_response.status_code == 200
    assert delete_response.json() == {
        "document_id": "doc-1",
        "document_count": 0,
    }
    assert search_response.json() == {"query": "python", "results": []}


def test_api_returns_404_for_missing_document_removal() -> None:
    client = TestClient(create_app())

    response = client.delete("/documents/missing")

    assert response.status_code == 404
    assert response.json() == {"detail": "Document 'missing' was not found."}


def test_api_clears_documents() -> None:
    client = TestClient(create_app())
    client.post(
        "/documents",
        json={
            "document_id": "doc-1",
            "text": "Python search engine",
        },
    )

    clear_response = client.post("/clear")
    search_response = client.post("/search", json={"query": "python"})

    assert clear_response.status_code == 200
    assert clear_response.json() == {"document_count": 0}
    assert search_response.json() == {"query": "python", "results": []}
