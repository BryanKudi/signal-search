from dataclasses import FrozenInstanceError

import pytest

from signal_search.api_models import (
    DocumentInput,
    SearchRequest,
    SearchResponse,
    SearchResultOutput,
    format_search_response,
)


def test_document_input_stores_document_payload() -> None:
    document = DocumentInput(
        document_id="doc-1",
        text="Python search engine",
    )

    assert document.document_id == "doc-1"
    assert document.text == "Python search engine"


def test_search_request_defaults_to_tfidf_ranking() -> None:
    request = SearchRequest(query="python")

    assert request.query == "python"
    assert request.use_tfidf is True


def test_search_request_can_choose_frequency_ranking() -> None:
    request = SearchRequest(query="python", use_tfidf=False)

    assert request.use_tfidf is False


def test_search_response_groups_query_and_ranked_results() -> None:
    result = SearchResultOutput(document_id="doc-1", score=2.5)
    response = SearchResponse(query="python", results=[result])

    assert response.query == "python"
    assert response.results == [result]


def test_api_models_are_immutable_contract_objects() -> None:
    request = SearchRequest(query="python")

    with pytest.raises(FrozenInstanceError):
        request.query = "rust"


def test_format_search_response_converts_ranked_tuples_to_output_models() -> None:
    response = format_search_response(
        query="python",
        results=[
            ("doc-1", 2),
            ("doc-2", 1.5),
        ],
    )

    assert response == SearchResponse(
        query="python",
        results=[
            SearchResultOutput(document_id="doc-1", score=2.0),
            SearchResultOutput(document_id="doc-2", score=1.5),
        ],
    )


def test_format_search_response_preserves_empty_results() -> None:
    response = format_search_response(query="missing", results=[])

    assert response == SearchResponse(query="missing", results=[])
