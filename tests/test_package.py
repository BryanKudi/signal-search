from signal_search import (
    DocumentInput,
    SearchEngine,
    SearchRequest,
    SearchResponse,
    SearchResultOutput,
    __version__,
    build_inverted_index,
    count_tokens,
    format_search_response,
    search,
    tfidf_search,
    tokenize,
)


def test_package_has_version() -> None:
    assert __version__ == "0.1.0"


def test_package_exports_public_search_tools() -> None:
    assert DocumentInput.__name__ == "DocumentInput"
    assert SearchEngine.__name__ == "SearchEngine"
    assert SearchRequest.__name__ == "SearchRequest"
    assert SearchResponse.__name__ == "SearchResponse"
    assert SearchResultOutput.__name__ == "SearchResultOutput"
    assert callable(build_inverted_index)
    assert callable(count_tokens)
    assert callable(format_search_response)
    assert callable(search)
    assert callable(tfidf_search)
    assert callable(tokenize)
