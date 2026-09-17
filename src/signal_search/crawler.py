"""Bounded breadth-first web crawling and HTML text extraction."""

import ipaddress
import socket
from collections import deque
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Callable, TypeAlias
from urllib.parse import urldefrag, urljoin, urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from urllib.robotparser import RobotFileParser

USER_AGENT = "SignalSearchBot/1.0 (+https://github.com/BryanKudi/signal-search)"
MAX_RESPONSE_BYTES = 2_000_000


@dataclass(frozen=True)
class CrawledPage:
    """Searchable content extracted from one web page."""

    url: str
    title: str
    text: str
    links: tuple[str, ...]


@dataclass(frozen=True)
class CrawlReport:
    """Pages and failures produced by a crawl."""

    pages: tuple[CrawledPage, ...]
    failed_urls: tuple[str, ...]


FetchPage: TypeAlias = Callable[[str, float], tuple[str, str]]


class _PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.text_parts: list[str] = []
        self.title_parts: list[str] = []
        self.links: list[str] = []
        self._ignored_depth = 0
        self._title_depth = 0

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        normalized_tag = tag.casefold()
        if normalized_tag in {"script", "style", "noscript"}:
            self._ignored_depth += 1
        elif normalized_tag == "title":
            self._title_depth += 1
        elif normalized_tag == "a":
            href = dict(attrs).get("href")
            if href:
                self.links.append(href)

    def handle_endtag(self, tag: str) -> None:
        normalized_tag = tag.casefold()
        if normalized_tag in {"script", "style", "noscript"}:
            self._ignored_depth = max(0, self._ignored_depth - 1)
        elif normalized_tag == "title":
            self._title_depth = max(0, self._title_depth - 1)

    def handle_data(self, data: str) -> None:
        if self._ignored_depth:
            return

        cleaned = " ".join(data.split())
        if not cleaned:
            return

        self.text_parts.append(cleaned)
        if self._title_depth:
            self.title_parts.append(cleaned)


class _SafeRedirectHandler(HTTPRedirectHandler):
    def redirect_request(
        self,
        req: Request,
        fp: object,
        code: int,
        msg: str,
        headers: object,
        newurl: str,
    ) -> Request | None:
        _ensure_public_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def extract_page(html: str, page_url: str) -> CrawledPage:
    """Extract normalized text and HTTP links from an HTML document."""
    parser = _PageParser()
    parser.feed(html)

    links: list[str] = []
    seen_links: set[str] = set()
    for href in parser.links:
        try:
            link = normalize_url(href, base_url=page_url)
        except ValueError:
            continue
        if link not in seen_links:
            seen_links.add(link)
            links.append(link)

    return CrawledPage(
        url=normalize_url(page_url),
        title=" ".join(parser.title_parts),
        text=" ".join(parser.text_parts),
        links=tuple(links),
    )


def normalize_url(url: str, *, base_url: str | None = None) -> str:
    """Resolve and normalize an HTTP URL while removing its fragment."""
    resolved = urljoin(base_url, url) if base_url else url
    without_fragment, _ = urldefrag(resolved)
    parsed = urlsplit(without_fragment)

    if parsed.scheme.casefold() not in {"http", "https"} or not parsed.hostname:
        raise ValueError(f"Unsupported URL: {url}")

    scheme = parsed.scheme.casefold()
    hostname = parsed.hostname.casefold()
    port = parsed.port
    default_port = (scheme == "http" and port == 80) or (
        scheme == "https" and port == 443
    )
    netloc = hostname if port is None or default_port else f"{hostname}:{port}"
    path = parsed.path or "/"
    return urlunsplit((scheme, netloc, path, parsed.query, ""))


def crawl_web(
    start_url: str,
    *,
    max_pages: int = 10,
    same_domain: bool = True,
    timeout: float = 5.0,
    fetch_page: FetchPage | None = None,
    respect_robots: bool = True,
) -> CrawlReport:
    """Crawl pages in breadth-first order within explicit safety bounds."""
    if not 1 <= max_pages <= 50:
        raise ValueError("max_pages must be between 1 and 50")
    if timeout <= 0:
        raise ValueError("timeout must be positive")

    root_url = normalize_url(start_url)
    crawl_hostname = urlsplit(root_url).hostname
    fetch = fetch_page or _fetch_page
    robots = _load_robots(root_url, timeout) if respect_robots else None
    queue: deque[str] = deque([root_url])
    queued = {root_url}
    visited: set[str] = set()
    pages: list[CrawledPage] = []
    failed_urls: list[str] = []

    while queue and len(pages) < max_pages:
        current_url = queue.popleft()
        if current_url in visited:
            continue
        visited.add(current_url)

        if robots is not None and not robots.can_fetch(USER_AGENT, current_url):
            failed_urls.append(current_url)
            continue

        try:
            html, final_url = fetch(current_url, timeout)
            page = extract_page(html, final_url)
        except (OSError, UnicodeError, ValueError):
            failed_urls.append(current_url)
            continue

        page_hostname = urlsplit(page.url).hostname
        if same_domain and pages and page_hostname != crawl_hostname:
            failed_urls.append(current_url)
            continue

        if not pages:
            crawl_hostname = page_hostname

        pages.append(page)

        for link in page.links:
            if same_domain and urlsplit(link).hostname != crawl_hostname:
                continue
            if link not in visited and link not in queued:
                queued.add(link)
                queue.append(link)

    return CrawlReport(pages=tuple(pages), failed_urls=tuple(failed_urls))


def _fetch_page(url: str, timeout: float) -> tuple[str, str]:
    _ensure_public_url(url)
    request = Request(url, headers={"User-Agent": USER_AGENT})
    opener = build_opener(_SafeRedirectHandler)

    with opener.open(request, timeout=timeout) as response:
        content_type = response.headers.get_content_type()
        if content_type not in {"text/html", "application/xhtml+xml"}:
            raise ValueError(f"Unsupported content type: {content_type}")

        payload = response.read(MAX_RESPONSE_BYTES + 1)
        if len(payload) > MAX_RESPONSE_BYTES:
            raise ValueError("Page exceeds the maximum response size")

        encoding = response.headers.get_content_charset() or "utf-8"
        return payload.decode(encoding), response.geturl()


def _ensure_public_url(url: str) -> None:
    hostname = urlsplit(url).hostname
    if hostname is None:
        raise ValueError("URL must include a hostname")

    addresses = socket.getaddrinfo(hostname, None)
    if not addresses:
        raise ValueError("URL hostname could not be resolved")

    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])
        if not ip.is_global:
            raise ValueError("Private and non-routable URLs cannot be crawled")


def _load_robots(start_url: str, timeout: float) -> RobotFileParser | None:
    parsed = urlsplit(start_url)
    robots_url = urlunsplit((parsed.scheme, parsed.netloc, "/robots.txt", "", ""))
    parser = RobotFileParser(robots_url)
    parser.set_url(robots_url)

    try:
        _ensure_public_url(robots_url)
        request = Request(robots_url, headers={"User-Agent": USER_AGENT})
        opener = build_opener(_SafeRedirectHandler)
        with opener.open(request, timeout=timeout) as response:
            payload = response.read(MAX_RESPONSE_BYTES)
            encoding = response.headers.get_content_charset() or "utf-8"
        parser.parse(payload.decode(encoding).splitlines())
    except (OSError, UnicodeError, ValueError):
        return None

    return parser
