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
    ranking: str | None = None
    limit: int | None = None
    offset: int = 0


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


@dataclass(frozen=True)
class CrawlRequest:
    """Bounded web crawl requested through the API."""

    start_url: str
    max_pages: int = 10
    same_domain: bool = True


@dataclass(frozen=True)
class CrawledPageOutput:
    """Summary of one page added by a crawl."""

    url: str
    title: str
    character_count: int


@dataclass(frozen=True)
class CrawlResponse:
    """Summary of a completed crawl and ingestion operation."""

    pages: list[CrawledPageOutput]
    failed_urls: list[str]
    indexed_count: int


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
