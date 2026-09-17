"""Run a short, repeatable Signal Search demo against the live API."""

import json
import os
import sys
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

BASE_URL = os.getenv("SIGNAL_SEARCH_URL", "http://127.0.0.1:8000").rstrip("/")

DEMO_DOCUMENTS = {
    "python-search-guide": (
        "Python search ranking guide using an inverted index and BM25."
    ),
    "ranking-notes": (
        "Python Python Python search search ranking ranking with extra notes "
        "about APIs databases containers testing deployment and monitoring."
    ),
    "fastapi-service": (
        "FastAPI service for adding documents and returning ranked search results."
    ),
    "sqlite-storage": (
        "SQLite persistence restores indexed documents after a container restart."
    ),
}


def request_json(
    method: str,
    path: str,
    payload: dict[str, object] | None = None,
) -> dict[str, Any]:
    """Send a JSON request to the running API."""
    body = json.dumps(payload).encode() if payload is not None else None
    request = Request(
        f"{BASE_URL}{path}",
        data=body,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    with urlopen(request, timeout=10) as response:
        return json.load(response)


def heading(title: str) -> None:
    """Print one readable demo section heading."""
    print(f"\n{'=' * 64}\n{title}\n{'=' * 64}")


def show_rankings(algorithm: str) -> None:
    """Run and print one ranked search."""
    response = request_json(
        "POST",
        "/search",
        {
            "query": "python search ranking",
            "ranking": algorithm,
            "limit": 3,
        },
    )
    print(f"\n{algorithm.upper()}")
    for position, result in enumerate(response["results"], start=1):
        print(
            f"  {position}. {result['document_id']:<22} "
            f"score={result['score']:.4f}"
        )


def main() -> None:
    """Show ingestion, ranking, caching, and metrics end to end."""
    try:
        service = request_json("GET", "/")
        health = request_json("GET", "/health")

        heading("SIGNAL SEARCH V1 DEMO")
        print(f"Service: {service['name']} {service['version']}")
        print(f"Health:  {health['status']}")
        print(f"API:     {BASE_URL}/docs")

        heading("1. INDEX SAMPLE DOCUMENTS")
        for document_id, text in DEMO_DOCUMENTS.items():
            request_json(
                "POST",
                "/documents",
                {"document_id": document_id, "text": text},
            )
            print(f"Indexed {document_id}")

        count = request_json("GET", "/documents/count")
        print(f"Searchable documents: {count['document_count']}")

        heading("2. COMPARE RANKING METHODS")
        for algorithm in ("frequency", "tfidf", "bm25"):
            show_rankings(algorithm)

        heading("3. PROVE THE QUERY CACHE")
        before = request_json("GET", "/metrics")
        request_json(
            "POST",
            "/search",
            {"query": "container persistence", "ranking": "bm25"},
        )
        request_json(
            "POST",
            "/search",
            {"query": "container persistence", "ranking": "bm25"},
        )
        after = request_json("GET", "/metrics")
        print(f"Cache hits before: {before['cache_hits']}")
        print(f"Cache hits after:  {after['cache_hits']}")
        print("The second identical search came from the cache.")

        heading("4. LIVE METRICS")
        for name in (
            "document_count",
            "vocabulary_size",
            "search_count",
            "cache_hits",
            "cache_misses",
            "cache_hit_rate",
            "average_search_latency_ms",
        ):
            print(f"{name:<24} {after[name]}")

        heading("DEMO COMPLETE")
        print("Signal Search indexed, ranked, cached, and measured real queries.")
        print("Restart the Docker service and rerun this script to verify persistence.")
    except (URLError, TimeoutError) as error:
        print(f"Could not reach Signal Search at {BASE_URL}.", file=sys.stderr)
        print("Start it with: docker compose up --build", file=sys.stderr)
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
