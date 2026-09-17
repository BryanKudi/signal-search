"""HTTP API for Signal Search."""

import os
from contextlib import asynccontextmanager
from dataclasses import asdict
from typing import Callable, cast

from fastapi import FastAPI, HTTPException, Query, status

from signal_search.api_models import (
    CrawledPageOutput,
    CrawlRequest,
    CrawlResponse,
    DocumentInput,
    SearchRequest,
    SearchResponse,
    format_search_response,
)
from signal_search.crawler import CrawlReport, crawl_web
from signal_search.engine import RankingAlgorithm, SearchEngine
from signal_search.storage import SQLiteDocumentStore
from signal_search.version import __version__

CrawlFunction = Callable[..., CrawlReport]


def create_app(
    engine: SearchEngine | None = None,
    crawler: CrawlFunction | None = None,
) -> FastAPI:
    """Create a FastAPI app backed by a search engine instance."""
    owns_engine = engine is None
    configured_engine = engine or create_default_engine()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        yield
        if owns_engine:
            configured_engine.close()

    app = FastAPI(title="Signal Search", version=__version__, lifespan=lifespan)
    app.state.engine = configured_engine
    app.state.crawler = crawler or crawl_web

    @app.get("/")
    def root() -> dict[str, str]:
        """Describe the API and its discovery endpoints."""
        return {
            "name": "Signal Search",
            "version": __version__,
            "docs": "/docs",
            "health": "/health",
        }

    @app.get("/health")
    def health() -> dict[str, str]:
        """Confirm the API process is running."""
        return {"status": "ok"}

    @app.get("/metrics")
    def metrics() -> dict[str, int | float]:
        """Return current index, cache, and query metrics."""
        return asdict(app.state.engine.metrics())

    @app.post("/documents", status_code=status.HTTP_201_CREATED)
    def add_document(document: DocumentInput) -> dict[str, str | int]:
        """Add or replace one searchable document."""
        if not document.document_id.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="document_id cannot be blank",
            )
        if not document.text.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="text cannot be blank",
            )

        app.state.engine.add_document(document.document_id, document.text)

        return {
            "document_id": document.document_id,
            "document_count": len(app.state.engine.documents),
        }

    @app.get("/documents/count")
    def count_documents() -> dict[str, int]:
        """Return how many documents are currently searchable."""
        return {"document_count": len(app.state.engine.documents)}

    @app.get("/documents")
    def list_documents(
        offset: int = Query(default=0, ge=0),
        limit: int = Query(default=100, ge=1, le=500),
    ) -> dict[str, int | list[dict[str, str | int]]]:
        """Return paginated document metadata without full document text."""
        items = sorted(app.state.engine.documents.items())
        documents = [
            {
                "document_id": document_id,
                "character_count": len(text),
            }
            for document_id, text in items[offset : offset + limit]
        ]

        return {
            "documents": documents,
            "document_count": len(items),
        }

    @app.get("/documents/{document_id}")
    def get_document(document_id: str) -> dict[str, str | int]:
        """Return one searchable document by ID."""
        text = app.state.engine.documents.get(document_id)

        if text is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document '{document_id}' was not found.",
            )

        return {
            "document_id": document_id,
            "text": text,
            "character_count": len(text),
        }

    @app.delete("/documents/{document_id}")
    def remove_document(document_id: str) -> dict[str, str | int]:
        """Remove one searchable document."""
        removed = app.state.engine.remove_document(document_id)

        if not removed:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document '{document_id}' was not found.",
            )

        return {
            "document_id": document_id,
            "document_count": len(app.state.engine.documents),
        }

    @app.post("/search")
    def search_documents(request: SearchRequest) -> SearchResponse:
        """Search documents with frequency, TF-IDF, or BM25 ranking."""
        if request.offset < 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="offset cannot be negative",
            )
        if request.limit is not None and not 1 <= request.limit <= 100:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="limit must be between 1 and 100",
            )

        selected_ranking = request.ranking
        if selected_ranking is None:
            selected_ranking = "tfidf" if request.use_tfidf else "frequency"
        if selected_ranking not in {"frequency", "tfidf", "bm25"}:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="ranking must be frequency, tfidf, or bm25",
            )

        algorithm = cast(RankingAlgorithm, selected_ranking)
        results = app.state.engine.rank(request.query, algorithm)
        end = None if request.limit is None else request.offset + request.limit
        paginated_results = results[request.offset:end]
        return format_search_response(
            query=request.query,
            results=paginated_results,
        )

    @app.post("/crawl", status_code=status.HTTP_201_CREATED)
    def crawl_documents(request: CrawlRequest) -> CrawlResponse:
        """Crawl and index a bounded collection of web pages."""
        try:
            report = app.state.crawler(
                request.start_url,
                max_pages=request.max_pages,
                same_domain=request.same_domain,
            )
        except ValueError as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=str(error),
            ) from error

        searchable_pages = {
            page.url: page.text for page in report.pages if page.text.strip()
        }
        app.state.engine.add_documents(searchable_pages)
        return CrawlResponse(
            pages=[
                CrawledPageOutput(
                    url=page.url,
                    title=page.title,
                    character_count=len(page.text),
                )
                for page in report.pages
            ],
            failed_urls=list(report.failed_urls),
            indexed_count=len(searchable_pages),
        )

    @app.post("/clear")
    def clear_documents() -> dict[str, int]:
        """Remove all searchable documents."""
        app.state.engine.clear()

        return {"document_count": len(app.state.engine.documents)}

    return app


def create_default_engine() -> SearchEngine:
    """Create an engine from optional environment configuration."""
    database_path = os.getenv("SIGNAL_SEARCH_DB_PATH")
    raw_cache_size = os.getenv("SIGNAL_SEARCH_CACHE_SIZE", "128")

    try:
        cache_size = int(raw_cache_size)
    except ValueError as error:
        raise RuntimeError("SIGNAL_SEARCH_CACHE_SIZE must be an integer") from error

    store = SQLiteDocumentStore(database_path) if database_path else None
    return SearchEngine(store=store, cache_size=cache_size)


app = create_app()
