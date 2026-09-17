"""Exercise a running Signal Search API using only the Python standard library."""

import json
import os
from urllib.request import Request, urlopen

BASE_URL = os.getenv("SIGNAL_SEARCH_URL", "http://127.0.0.1:8000").rstrip("/")


def request_json(
    method: str,
    path: str,
    payload: dict[str, object] | None = None,
) -> dict[str, object]:
    """Send one JSON request and return its decoded object response."""
    body = json.dumps(payload).encode() if payload is not None else None
    request = Request(
        f"{BASE_URL}{path}",
        data=body,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    with urlopen(request, timeout=5) as response:
        return json.load(response)


def main() -> None:
    """Verify health, ingestion, ranking, and metrics end to end."""
    health = request_json("GET", "/health")
    assert health == {"status": "ok"}

    document_id = "container-smoke-test"
    request_json(
        "POST",
        "/documents",
        {
            "document_id": document_id,
            "text": "Python search engine with BM25 ranking",
        },
    )
    search = request_json(
        "POST",
        "/search",
        {"query": "python ranking", "ranking": "bm25"},
    )
    results = search["results"]
    assert isinstance(results, list)
    assert any(
        isinstance(result, dict) and result.get("document_id") == document_id
        for result in results
    )

    metrics = request_json("GET", "/metrics")
    assert metrics["document_count"] >= 1
    assert metrics["search_count"] >= 1
    print("Signal Search smoke test passed.")


if __name__ == "__main__":
    main()
