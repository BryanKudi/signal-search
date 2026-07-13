from dataclasses import FrozenInstanceError

import pytest

from signal_search.api_models import (
    DocumentInput,
    SearchRequest,
    SearchResponse,
    SearchResultOutput,
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
