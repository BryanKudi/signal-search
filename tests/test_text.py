import pytest

from signal_search.text import tokenize


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

