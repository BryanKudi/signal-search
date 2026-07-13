"""Request and response models for the future HTTP API."""

from dataclasses import dataclass


@dataclass(frozen=True)
class DocumentInput:
    """Document payload accepted by the API."""

    document_id: str
    text: str


@dataclass(frozen=True)
class SearchRequest:
    """Search query payload accepted by the API."""

    query: str
    use_tfidf: bool = True


@dataclass(frozen=True)
class SearchResultOutput:
    """One ranked search result returned by the API."""

    document_id: str
    score: float


@dataclass(frozen=True)
class SearchResponse:
    """Complete search response returned by the API."""

    query: str
    results: list[SearchResultOutput]
