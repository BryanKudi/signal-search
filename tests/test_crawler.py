from signal_search.crawler import crawl_web, extract_page, normalize_url


def test_extract_page_collects_visible_text_and_normalized_links() -> None:
    page = extract_page(
        """
        <html>
          <head>
            <title>Signal Search</title>
            <style>hidden style</style>
          </head>
          <body>
            <h1>Python Search</h1>
            <script>hidden script</script>
            <a href="/docs#intro">Docs</a>
            <a href="/docs#other">Duplicate</a>
            <a href="mailto:test@example.com">Email</a>
          </body>
        </html>
        """,
        "https://example.com/start",
    )

    assert page.url == "https://example.com/start"
    assert page.title == "Signal Search"
    assert "Python Search" in page.text
    assert "hidden" not in page.text
    assert page.links == ("https://example.com/docs",)


def test_crawler_visits_pages_in_breadth_first_order() -> None:
    pages = {
        "https://example.com/": (
            '<a href="/a">A</a><a href="/b">B</a>',
            "https://example.com/",
        ),
        "https://example.com/a": (
            '<p>Page A</p><a href="/c">C</a>',
            "https://example.com/a",
        ),
        "https://example.com/b": (
            "<p>Page B</p>",
            "https://example.com/b",
        ),
        "https://example.com/c": (
            "<p>Page C</p>",
            "https://example.com/c",
        ),
    }

    def fetch_page(url: str, _: float) -> tuple[str, str]:
        return pages[url]

    report = crawl_web(
        "https://example.com",
        max_pages=3,
        fetch_page=fetch_page,
        respect_robots=False,
    )

    assert [page.url for page in report.pages] == [
        "https://example.com/",
        "https://example.com/a",
        "https://example.com/b",
    ]
    assert report.failed_urls == ()


def test_crawler_stays_on_the_starting_domain() -> None:
    def fetch_page(url: str, _: float) -> tuple[str, str]:
        return (
            '<a href="https://other.example/page">Other</a>',
            url,
        )

    report = crawl_web(
        "https://example.com",
        fetch_page=fetch_page,
        respect_robots=False,
    )

    assert len(report.pages) == 1


def test_crawler_records_fetch_failures() -> None:
    def fetch_page(url: str, _: float) -> tuple[str, str]:
        raise OSError("unavailable")

    report = crawl_web(
        "https://example.com",
        fetch_page=fetch_page,
        respect_robots=False,
    )

    assert report.pages == ()
    assert report.failed_urls == ("https://example.com/",)


def test_normalize_url_rejects_non_http_protocols() -> None:
    try:
        normalize_url("file:///tmp/private.txt")
    except ValueError as error:
        assert "Unsupported URL" in str(error)
    else:
        raise AssertionError("Expected unsupported URL error")
