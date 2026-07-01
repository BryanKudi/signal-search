# Signal Search

Signal Search is a learning-focused search engine built from first principles in
Python. The project connects data structures and algorithms to production-style
software engineering and system design.

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

