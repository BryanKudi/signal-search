from fastapi.testclient import TestClient

from signal_search.api import create_app
from signal_search.crawler import CrawledPage, CrawlReport


def test_root_endpoint_describes_api() -> None:
    client = TestClient(create_app())

    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "name": "Signal Search",
        "version": "1.0.0",
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


def test_api_lists_document_metadata() -> None:
    client = TestClient(create_app())
    client.post(
        "/documents",
        json={
            "document_id": "doc-2",
            "text": "Rust systems",
        },
    )
    client.post(
        "/documents",
        json={
            "document_id": "doc-1",
            "text": "Python search engine",
        },
    )

    response = client.get("/documents")

    assert response.status_code == 200
    assert response.json() == {
        "documents": [
            {
                "document_id": "doc-1",
                "character_count": 20,
            },
            {
                "document_id": "doc-2",
                "character_count": 12,
            },
        ],
        "document_count": 2,
    }


def test_api_gets_document_by_id() -> None:
    client = TestClient(create_app())
    client.post(
        "/documents",
        json={
            "document_id": "doc-1",
            "text": "Python search engine",
        },
    )

    response = client.get("/documents/doc-1")

    assert response.status_code == 200
    assert response.json() == {
        "document_id": "doc-1",
        "text": "Python search engine",
        "character_count": 20,
    }


def test_api_returns_404_when_getting_missing_document() -> None:
    client = TestClient(create_app())

    response = client.get("/documents/missing")

    assert response.status_code == 404
    assert response.json() == {"detail": "Document 'missing' was not found."}


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


def test_api_searches_with_bm25_and_pagination() -> None:
    client = TestClient(create_app())
    for document_id, text in {
        "doc-1": "python search",
        "doc-2": "python python engine",
        "doc-3": "python systems",
    }.items():
        client.post(
            "/documents",
            json={"document_id": document_id, "text": text},
        )

    response = client.post(
        "/search",
        json={
            "query": "python",
            "ranking": "bm25",
            "offset": 1,
            "limit": 1,
        },
    )

    assert response.status_code == 200
    assert response.json()["query"] == "python"
    assert len(response.json()["results"]) == 1
    assert response.json()["results"][0]["document_id"] == "doc-1"


def test_api_rejects_invalid_ranking_and_pagination() -> None:
    client = TestClient(create_app())

    ranking_response = client.post(
        "/search",
        json={"query": "python", "ranking": "pagerank"},
    )
    pagination_response = client.post(
        "/search",
        json={"query": "python", "limit": 101},
    )

    assert ranking_response.status_code == 422
    assert pagination_response.status_code == 422


def test_api_returns_search_and_cache_metrics() -> None:
    client = TestClient(create_app())
    client.post(
        "/documents",
        json={"document_id": "doc-1", "text": "Python search engine"},
    )
    client.post("/search", json={"query": "python"})
    client.post("/search", json={"query": "PYTHON!"})

    response = client.get("/metrics")

    assert response.status_code == 200
    assert response.json()["document_count"] == 1
    assert response.json()["vocabulary_size"] == 3
    assert response.json()["search_count"] == 2
    assert response.json()["cache_hits"] == 1
    assert response.json()["cache_misses"] == 1
    assert response.json()["cache_hit_rate"] == 0.5


def test_api_crawls_and_indexes_pages() -> None:
    def fake_crawler(
        start_url: str,
        *,
        max_pages: int,
        same_domain: bool,
    ) -> CrawlReport:
        assert start_url == "https://example.com"
        assert max_pages == 2
        assert same_domain is True
        return CrawlReport(
            pages=(
                CrawledPage(
                    url="https://example.com/",
                    title="Example",
                    text="Python search engine",
                    links=(),
                ),
            ),
            failed_urls=("https://example.com/missing",),
        )

    client = TestClient(create_app(crawler=fake_crawler))

    crawl_response = client.post(
        "/crawl",
        json={
            "start_url": "https://example.com",
            "max_pages": 2,
        },
    )
    search_response = client.post(
        "/search",
        json={"query": "python", "ranking": "bm25"},
    )

    assert crawl_response.status_code == 201
    assert crawl_response.json() == {
        "pages": [
            {
                "url": "https://example.com/",
                "title": "Example",
                "character_count": 20,
            }
        ],
        "failed_urls": ["https://example.com/missing"],
        "indexed_count": 1,
    }
    assert search_response.json()["results"][0]["document_id"] == (
        "https://example.com/"
    )


def test_api_rejects_blank_documents() -> None:
    client = TestClient(create_app())

    blank_id = client.post(
        "/documents",
        json={"document_id": "  ", "text": "search"},
    )
    blank_text = client.post(
        "/documents",
        json={"document_id": "doc-1", "text": "  "},
    )

    assert blank_id.status_code == 422
    assert blank_text.status_code == 422
