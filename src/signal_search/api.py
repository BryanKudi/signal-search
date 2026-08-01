"""HTTP API for Signal Search."""

from fastapi import FastAPI, HTTPException, status

from signal_search.api_models import (
    DocumentInput,
    SearchRequest,
    SearchResponse,
    format_search_response,
)
from signal_search.engine import SearchEngine


def create_app(engine: SearchEngine | None = None) -> FastAPI:
    """Create a FastAPI app backed by a search engine instance."""
    app = FastAPI(title="Signal Search", version="0.1.0")
    app.state.engine = engine or SearchEngine()

    @app.get("/")
    def root() -> dict[str, str]:
        """Describe the API and its discovery endpoints."""
        return {
            "name": "Signal Search",
            "version": "0.1.0",
            "docs": "/docs",
            "health": "/health",
        }

    @app.get("/health")
    def health() -> dict[str, str]:
        """Confirm the API process is running."""
        return {"status": "ok"}

    @app.post("/documents", status_code=status.HTTP_201_CREATED)
    def add_document(document: DocumentInput) -> dict[str, str | int]:
        """Add or replace one searchable document."""
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
    def list_documents() -> dict[str, int | list[dict[str, str | int]]]:
        """Return searchable document metadata without full document text."""
        documents = [
            {
                "document_id": document_id,
                "character_count": len(text),
            }
            for document_id, text in sorted(app.state.engine.documents.items())
        ]

        return {
            "documents": documents,
            "document_count": len(documents),
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
        """Search documents with frequency or TF-IDF ranking."""
        if request.use_tfidf:
            results = app.state.engine.tfidf_search(request.query)
        else:
            results = app.state.engine.search(request.query)

        return format_search_response(query=request.query, results=results)

    @app.post("/clear")
    def clear_documents() -> dict[str, int]:
        """Remove all searchable documents."""
        app.state.engine.clear()

        return {"document_count": len(app.state.engine.documents)}

    return app


app = create_app()
