import pytest

from signal_search.text import count_tokens, tokenize


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Signal Search", ["signal", "search"]),
        ("PYTHON, Python!", ["python", "python"]),
        ("graph-based   ranking", ["graph", "based", "ranking"]),
        ("Version 2", ["version", "2"]),
        ("", []),
        ("...", []),
    ],
)
def test_tokenize(text: str, expected: list[str]) -> None:
    assert tokenize(text) == expected


def test_tokenize_supports_unicode_letters() -> None:
    assert tokenize("Café CAFÉ") == ["café", "café"]


def test_count_tokens_counts_repeated_tokens() -> None:
    tokens = ["python", "search", "python"]

    assert count_tokens(tokens) == {"python": 2, "search": 1}


def test_count_tokens_accepts_an_empty_list() -> None:
    assert count_tokens([]) == {}
