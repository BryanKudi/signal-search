"""In-memory inverted index construction."""

from signal_search.text import count_tokens, tokenize


def build_inverted_index(
    documents: dict[str, str],
) -> dict[str, dict[str, int]]:
    """Map each token to its frequency in every containing document."""
    index: dict[str, dict[str, int]] = {}

    for document_id, text in documents.items():
        frequencies = count_tokens(tokenize(text))

        for token, frequency in frequencies.items():
            if token not in index:
                index[token] = {}

            index[token][document_id] = frequency

    return index
