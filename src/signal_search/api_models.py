"""Request and response models for the future HTTP API."""

from dataclasses import dataclass

RawSearchResult = tuple[str, int | float]


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


def format_search_response(
    query: str,
    results: list[RawSearchResult],
) -> SearchResponse:
    """Convert internal ranked tuples into an API response object."""
    return SearchResponse(
        query=query,
        results=[
            SearchResultOutput(document_id=document_id, score=float(score))
            for document_id, score in results
        ],
    )
