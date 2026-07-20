"""High-level search engine service."""

from dataclasses import dataclass, field

from signal_search.index import build_inverted_index
from signal_search.search import (
    InvertedIndex,
    SearchResult,
    TFIDFResult,
    search as frequency_search,
    tfidf_search as rank_with_tfidf,
)


@dataclass
class SearchEngine:
    """Store documents, build an index, and run searches against it."""

    documents: dict[str, str] = field(default_factory=dict)
    index: InvertedIndex = field(default_factory=dict)

    def add_document(self, document_id: str, text: str) -> None:
        """Add or replace one document and rebuild the index."""
        self.documents[document_id] = text
        self.index = build_inverted_index(self.documents)

    def add_documents(self, documents: dict[str, str]) -> None:
        """Add or replace multiple documents and rebuild the index once."""
        self.documents.update(documents)
        self.index = build_inverted_index(self.documents)

    def remove_document(self, document_id: str) -> bool:
        """Remove one document if it exists and rebuild the index."""
        if document_id not in self.documents:
            return False

        del self.documents[document_id]
        self.index = build_inverted_index(self.documents)
        return True

    def clear(self) -> None:
        """Remove all documents and reset the index."""
        self.documents.clear()
        self.index.clear()

    def search(self, query: str) -> list[SearchResult]:
        """Return documents ranked by raw token frequency."""
        return frequency_search(self.index, query)

    def tfidf_search(self, query: str) -> list[TFIDFResult]:
        """Return documents ranked by TF-IDF relevance."""
        if not self.documents:
            return []

        return rank_with_tfidf(
            self.index,
            query,
            total_documents=len(self.documents),
        )
