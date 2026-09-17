# Signal Search

Signal Search is a complete, learning-focused search engine built from first
principles in Python. It crawls and indexes web pages, ranks documents with
multiple relevance algorithms, persists content in SQLite, caches repeated
queries, and exposes the system through a tested FastAPI service.

**Release:** v1.0.0

## Features

- Unicode-aware text normalization and tokenization.
- Incrementally maintained inverted index with term frequencies.
- Raw-frequency, smoothed TF-IDF, and BM25 ranking.
- Bounded breadth-first web crawler with same-domain controls.
- Robots.txt support, response-size limits, and private-network protection.
- SQLite persistence that restores the index after a restart.
- Thread-safe document mutations and searches.
- LRU query cache with automatic invalidation after index changes.
- Pagination for document listings and search results.
- Operational metrics for query latency, cache performance, and index size.
- FastAPI-generated OpenAPI documentation.
- Docker deployment configuration.
- Automated pytest and GitHub Actions coverage.

## Architecture

```text
Web pages / API documents
          |
          v
  normalization + tokenization
          |
          v
    incremental inverted index <---- SQLite document store
          |
          v
 frequency / TF-IDF / BM25 ranking
          |
          v
       LRU query cache
          |
          v
        FastAPI API
```

The inverted index maps each token to the documents containing it and the
token frequency within each document:

```python
{
    "python": {
        "doc-1": 2,
        "doc-2": 1,
    }
}
```

Documents can remain fully in memory for tests and short-lived demos, or they
can be persisted in SQLite by setting `SIGNAL_SEARCH_DB_PATH`. The index is
reconstructed from persisted documents when the service starts.

## Local Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
pytest
```

Start the API:

```bash
uvicorn signal_search.api:app --reload
```

Open the interactive documentation at:

```text
http://127.0.0.1:8000/docs
```

## Persistent Mode

```bash
export SIGNAL_SEARCH_DB_PATH=./data/signal-search.db
export SIGNAL_SEARCH_CACHE_SIZE=256
uvicorn signal_search.api:app --reload
```

Supported environment variables:

| Variable | Default | Purpose |
| --- | --- | --- |
| `SIGNAL_SEARCH_DB_PATH` | unset | Enables SQLite persistence at the selected path |
| `SIGNAL_SEARCH_CACHE_SIZE` | `128` | Maximum number of cached ranking results |

## API

### Add a document

```bash
curl -X POST http://127.0.0.1:8000/documents \
  -H "Content-Type: application/json" \
  -d '{"document_id":"python-guide","text":"Python search engine guide"}'
```

### Search with BM25

```bash
curl -X POST http://127.0.0.1:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query":"python search","ranking":"bm25","limit":10,"offset":0}'
```

Available ranking values are `frequency`, `tfidf`, and `bm25`. Existing clients
can continue using `use_tfidf`; an explicit `ranking` value takes precedence.

### Crawl and index a site

```bash
curl -X POST http://127.0.0.1:8000/crawl \
  -H "Content-Type: application/json" \
  -d '{"start_url":"https://example.com","max_pages":10,"same_domain":true}'
```

The crawler uses breadth-first traversal, accepts at most 50 pages per request,
follows robots.txt rules when available, rejects private or non-routable hosts,
and limits each response body to 2 MB.

### Available endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/` | API discovery information |
| `GET` | `/health` | Process health check |
| `GET` | `/metrics` | Search, cache, and index metrics |
| `POST` | `/documents` | Add or replace a document |
| `GET` | `/documents` | List paginated document metadata |
| `GET` | `/documents/count` | Count indexed documents |
| `GET` | `/documents/{document_id}` | Retrieve a document |
| `DELETE` | `/documents/{document_id}` | Remove a document |
| `POST` | `/search` | Search with a selected ranking algorithm |
| `POST` | `/crawl` | Crawl and index web pages |
| `POST` | `/clear` | Remove every indexed document |

## Docker

The shortest setup is the same on macOS, Windows, and Linux:

```bash
docker compose up --build
```

After the container becomes healthy, open `http://localhost:8000/docs` or run:

```bash
python scripts/smoke_test.py
```

Compose stores SQLite data in a Docker-managed named volume, avoiding
host-specific file paths and permissions. To stop the service, run
`docker compose down`. Add `--volumes` only when you intentionally want to
delete the persisted index.

The lower-level Docker commands are also available:

```bash
docker build -t signal-search .
docker run --rm -p 8000:8000 signal-search
```

The image uses a pinned Python 3.12 runtime and locked production dependencies.
The official Python base image supports both AMD64/Intel and ARM64 hardware.
CI builds and smoke-tests both architectures, while the Python suite runs on
Python 3.11, 3.12, and 3.13.

## Recruiter Demo

With the API running, launch the repeatable demo:

```bash
python scripts/demo.py
```

The script indexes four sample documents, compares frequency, TF-IDF, and BM25
ranking, proves that repeated searches use the cache, and prints live service
metrics. It only uses the Python standard library and does not require internet
access.

## Testing

```bash
pytest
```

The suite verifies tokenization, incremental indexing, every ranking strategy,
cache behavior, persistence across engine restarts, crawler traversal and HTML
extraction, API validation, pagination, metrics, and document lifecycle flows.

GitHub Actions runs the suite on three Python versions and builds runnable AMD64
and ARM64 containers for pushes and pull requests targeting `dev`, `staging`,
or `main`.

## Design Decisions

- **Incremental indexing:** document changes update only affected posting lists
  instead of rebuilding the complete index.
- **BM25 as the production ranking option:** BM25 accounts for document length,
  while frequency and TF-IDF remain available for comparison and learning.
- **SQLite persistence:** SQLite keeps deployment simple while providing durable,
  transactional document storage.
- **Bounded crawling:** strict page, domain, payload, and network controls prevent
  an API request from becoming an unlimited crawl.
- **In-process LRU caching:** repeated normalized queries avoid ranking work while
  every document mutation invalidates stale results.
- **Deterministic ties:** equal scores are ordered by document ID, keeping tests
  and API responses reproducible.

## Project Scope

Version 1.0 is complete as a standalone single-node search service. Distributed
indexing, semantic vector search, authentication, and a browser-based frontend
are possible future extensions, not requirements for the completed release.

## Development Workflow

Changes move through `feature/* -> dev -> staging -> main` using pull requests.
