"""High-level search engine service."""

from collections import OrderedDict
from dataclasses import dataclass
from threading import RLock
from time import perf_counter
from typing import Literal, TypeAlias

from signal_search.index import (
    InvertedIndex,
    add_document_to_index,
    build_inverted_index,
    remove_document_from_index,
)
from signal_search.search import (
    BM25Result,
    SearchResult,
    TFIDFResult,
    bm25_search as rank_with_bm25,
    search as frequency_search,
    tfidf_search as rank_with_tfidf,
)
from signal_search.storage import DocumentStore
from signal_search.text import tokenize

RankingAlgorithm = Literal["frequency", "tfidf", "bm25"]
RankedResult: TypeAlias = SearchResult | TFIDFResult | BM25Result


@dataclass(frozen=True)
class MetricsSnapshot:
    """Point-in-time operational metrics for the search engine."""

    document_count: int
    vocabulary_size: int
    search_count: int
    cache_hits: int
    cache_misses: int
    cache_entries: int
    cache_hit_rate: float
    average_search_latency_ms: float


class SearchEngine:
    """Store documents, maintain an index, and run ranked searches."""

    def __init__(
        self,
        documents: dict[str, str] | None = None,
        *,
        store: DocumentStore | None = None,
        cache_size: int = 128,
    ) -> None:
        if cache_size < 0:
            raise ValueError("cache_size cannot be negative")

        self.store = store
        self.cache_size = cache_size
        self._lock = RLock()
        persisted_documents = store.load_documents() if store is not None else {}
        self.documents = persisted_documents

        if documents:
            self.documents.update(documents)
            if store is not None:
                store.upsert_documents(documents)

        self.index: InvertedIndex = build_inverted_index(self.documents)
        self.document_lengths = {
            document_id: len(tokenize(text))
            for document_id, text in self.documents.items()
        }
        self._cache: OrderedDict[
            tuple[RankingAlgorithm, tuple[str, ...]],
            tuple[RankedResult, ...],
        ] = OrderedDict()
        self._search_count = 0
        self._cache_hits = 0
        self._cache_misses = 0
        self._total_search_latency_ms = 0.0

    def add_document(self, document_id: str, text: str) -> None:
        """Add or replace one document and update affected postings."""
        with self._lock:
            if self.store is not None:
                self.store.upsert_document(document_id, text)

            if document_id in self.documents:
                remove_document_from_index(self.index, document_id)

            self.documents[document_id] = text
            self.document_lengths[document_id] = len(tokenize(text))
            add_document_to_index(self.index, document_id, text)
            self._invalidate_cache()

    def add_documents(self, documents: dict[str, str]) -> None:
        """Add or replace multiple documents and update affected postings."""
        with self._lock:
            if self.store is not None:
                self.store.upsert_documents(documents)

            for document_id, text in documents.items():
                if document_id in self.documents:
                    remove_document_from_index(self.index, document_id)
                self.documents[document_id] = text
                self.document_lengths[document_id] = len(tokenize(text))
                add_document_to_index(self.index, document_id, text)

            self._invalidate_cache()

    def remove_document(self, document_id: str) -> bool:
        """Remove one document if it exists and update affected postings."""
        with self._lock:
            if document_id not in self.documents:
                return False

            if self.store is not None:
                self.store.delete_document(document_id)

            del self.documents[document_id]
            self.document_lengths.pop(document_id, None)
            remove_document_from_index(self.index, document_id)
            self._invalidate_cache()
            return True

    def clear(self) -> None:
        """Remove all documents, index data, and cached results."""
        with self._lock:
            if self.store is not None:
                self.store.clear()

            self.documents.clear()
            self.index.clear()
            self.document_lengths.clear()
            self._invalidate_cache()

    def search(self, query: str) -> list[SearchResult]:
        """Return documents ranked by raw token frequency."""
        return list(self._rank(query, "frequency"))

    def tfidf_search(self, query: str) -> list[TFIDFResult]:
        """Return documents ranked by TF-IDF relevance."""
        return list(self._rank(query, "tfidf"))

    def bm25_search(self, query: str) -> list[BM25Result]:
        """Return documents ranked by BM25 relevance."""
        return list(self._rank(query, "bm25"))

    def rank(
        self,
        query: str,
        algorithm: RankingAlgorithm = "bm25",
    ) -> list[RankedResult]:
        """Run a query with the selected ranking algorithm."""
        return list(self._rank(query, algorithm))

    def metrics(self) -> MetricsSnapshot:
        """Return current index, cache, and search metrics."""
        with self._lock:
            attempts = self._cache_hits + self._cache_misses
            hit_rate = self._cache_hits / attempts if attempts else 0.0
            average_latency = (
                self._total_search_latency_ms / self._search_count
                if self._search_count
                else 0.0
            )
            return MetricsSnapshot(
                document_count=len(self.documents),
                vocabulary_size=len(self.index),
                search_count=self._search_count,
                cache_hits=self._cache_hits,
                cache_misses=self._cache_misses,
                cache_entries=len(self._cache),
                cache_hit_rate=hit_rate,
                average_search_latency_ms=average_latency,
            )

    def close(self) -> None:
        """Release resources owned by the configured storage backend."""
        with self._lock:
            if self.store is not None:
                self.store.close()

    def _rank(
        self,
        query: str,
        algorithm: RankingAlgorithm,
    ) -> tuple[RankedResult, ...]:
        with self._lock:
            if algorithm not in {"frequency", "tfidf", "bm25"}:
                raise ValueError(f"Unsupported ranking algorithm: {algorithm}")

            started_at = perf_counter()
            cache_key = (algorithm, tuple(sorted(set(tokenize(query)))))

            if cache_key in self._cache:
                self._cache_hits += 1
                self._cache.move_to_end(cache_key)
                results = self._cache[cache_key]
            else:
                self._cache_misses += 1
                results = tuple(self._compute_rank(query, algorithm))
                self._store_cache_entry(cache_key, results)

            self._search_count += 1
            self._total_search_latency_ms += (perf_counter() - started_at) * 1000
            return results

    def _compute_rank(
        self,
        query: str,
        algorithm: RankingAlgorithm,
    ) -> list[RankedResult]:
        if algorithm == "frequency":
            return frequency_search(self.index, query)

        if not self.documents:
            return []

        if algorithm == "tfidf":
            return rank_with_tfidf(
                self.index,
                query,
                total_documents=len(self.documents),
            )

        total_tokens = sum(self.document_lengths.values())
        average_document_length = total_tokens / len(self.documents)
        return rank_with_bm25(
            self.index,
            query,
            self.document_lengths,
            total_documents=len(self.documents),
            average_document_length=average_document_length,
        )

    def _store_cache_entry(
        self,
        key: tuple[RankingAlgorithm, tuple[str, ...]],
        results: tuple[RankedResult, ...],
    ) -> None:
        if self.cache_size == 0:
            return

        self._cache[key] = results
        self._cache.move_to_end(key)

        while len(self._cache) > self.cache_size:
            self._cache.popitem(last=False)

    def _invalidate_cache(self) -> None:
        self._cache.clear()
