"""In-memory inverted index construction."""

from signal_search.text import count_tokens, tokenize

InvertedIndex = dict[str, dict[str, int]]


def build_inverted_index(
    documents: dict[str, str],
) -> InvertedIndex:
    """Map each token to its frequency in every containing document."""
    index: dict[str, dict[str, int]] = {}

    for document_id, text in documents.items():
        frequencies = count_tokens(tokenize(text))

        for token, frequency in frequencies.items():
            documents_for_token = index.get(token)
            if documents_for_token is None:
                index[token] = {document_id: frequency}
            else:
                documents_for_token[document_id] = frequency

    return index


def add_document_to_index(
    index: InvertedIndex,
    document_id: str,
    text: str,
) -> None:
    """Add one document's token frequencies to an existing index."""
    for token, frequency in count_tokens(tokenize(text)).items():
        index.setdefault(token, {})[document_id] = frequency


def remove_document_from_index(
    index: InvertedIndex,
    document_id: str,
) -> None:
    """Remove one document from every posting list in an index."""
    empty_tokens: list[str] = []

    for token, postings in index.items():
        postings.pop(document_id, None)
        if not postings:
            empty_tokens.append(token)

    for token in empty_tokens:
        del index[token]
