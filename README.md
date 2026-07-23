# Signal Search

Signal Search is a learning-focused search engine built from first principles in
Python. The project connects data structures and algorithms to production-style
software engineering and system design.

**Status:** In progress. The current version supports text normalization,
inverted indexing, frequency ranking, TF-IDF ranking, a FastAPI search API, and
automated tests.

## What works now

- Tokenizes and normalizes document text.
- Builds an in-memory inverted index from document IDs to token frequencies.
- Searches documents with raw frequency scoring.
- Ranks results with smoothed TF-IDF scoring.
- Exposes document ingestion, deletion, clearing, health checks, and search
  through FastAPI.
- Verifies behavior with pytest and GitHub Actions.

## Learning goals

- Crawl documents with graph traversal.
- Build an inverted index with hash-based data structures.
- Rank results with TF-IDF, BM25, heaps, and graph algorithms.
- Expose search through a tested API.
- Add persistence, caching, background work, observability, and deployment.

## Development workflow

Changes move through `feature/* -> dev -> staging -> main` using pull requests.

## Local setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
pytest
```

## Run the API locally

```bash
uvicorn signal_search.api:app --reload
```

Then open:

```text
http://127.0.0.1:8000/docs
```

The API currently supports:

- `GET /health`
- `POST /documents`
- `DELETE /documents/{document_id}`
- `POST /search`
- `POST /clear`

## Roadmap

- Add BM25 ranking.
- Persist indexes and documents beyond process memory.
- Add caching for repeated queries.
- Crawl documents with graph traversal.
- Add observability for query latency and indexing behavior.
