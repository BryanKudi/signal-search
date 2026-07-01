"""Text normalization used by the search index."""


def tokenize(text: str) -> list[str]:
    """Convert text into lowercase alphanumeric search tokens.

    A token ends whenever a non-alphanumeric character is encountered. Repeated
    tokens are preserved because their frequency will later influence ranking.
    """
    tokens: list[str] = []
    current: list[str] = []

    for character in text.casefold():
        if character.isalnum():
            current.append(character)
        elif current:
            tokens.append("".join(current))
            current.clear()

    if current:
        tokens.append("".join(current))

    return tokens


def count_tokens(tokens: list[str]) -> dict[str, int]:
    """Count how many times each token appears."""
    counts: dict[str, int] = {}

    for token in tokens:
        counts[token] = counts.get(token, 0) + 1

    return counts
