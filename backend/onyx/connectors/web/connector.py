import gzip
import io
import ipaddress
import random
import socket
import time
from datetime import datetime
from datetime import timezone
from enum import Enum
from typing import Any
from typing import cast
from urllib.parse import urljoin
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import BrowserContext
from playwright.sync_api import Playwright
from playwright.sync_api import Request
from playwright.sync_api import Route
from playwright.sync_api import TimeoutError
from typing_extensions import override
from urllib3.exceptions import MaxRetryError

from onyx.configs.app_configs import INDEX_BATCH_SIZE
from onyx.configs.app_configs import REQUEST_TIMEOUT_SECONDS
from onyx.configs.constants import DocumentSource
from onyx.connectors.exceptions import ConnectorValidationError
from onyx.connectors.exceptions import CredentialExpiredError
from onyx.connectors.exceptions import InsufficientPermissionsError
from onyx.connectors.exceptions import UnexpectedValidationError
from onyx.connectors.interfaces import GenerateDocumentsOutput
from onyx.connectors.interfaces import GenerateSlimDocumentOutput
from onyx.connectors.interfaces import LoadConnector
from onyx.connectors.interfaces import SecondsSinceUnixEpoch
from onyx.connectors.interfaces import SlimConnector
from onyx.connectors.models import Document
from onyx.connectors.models import HierarchyNode
from onyx.connectors.models import SlimDocument
from onyx.connectors.models import TextSection
from onyx.db.document import get_documents_updated_at_batch
from onyx.db.engine.sql_engine import get_session_with_current_tenant
from onyx.file_processing.extract_file_text import read_pdf_file
from onyx.file_processing.html_utils import web_html_cleanup
from onyx.indexing.indexing_heartbeat import IndexingHeartbeatInterface
from onyx.server.security.models import web_connector_ssrf_enforced
from onyx.server.security.store import get_security_settings
from onyx.utils.logger import setup_logger

# Re-exported for backwards compatibility with existing tests/callers that
# patch these names on `onyx.connectors.web.connector`.
from onyx.utils.playwright_fetch import DEFAULT_HEADERS
from onyx.utils.playwright_fetch import DEFAULT_USER_AGENT  # noqa: F401
from onyx.utils.playwright_fetch import start_playwright
from onyx.utils.sitemap import list_pages_for_site
from onyx.utils.eea_utils import (
    is_pdf_mime_type,
    list_pages_for_site_eea,
    list_pages_for_protected_site_eea,
    soer_login,
    remove_by_selector,
)
from onyx.utils.web_content import extract_pdf_text
from onyx.utils.web_content import is_pdf_resource
from shared_configs.configs import MULTI_TENANT

logger = setup_logger()

# EEA: Global auth state for protected site crawling (SOER)
eea_global_auth: dict[str, Any] = {}


class ScrapeSessionContext:
    """Session level context for scraping"""

    def __init__(self, base_url: str, to_visit: list[str], lastmod: list[str | None]):
        self.base_url = base_url
        self.to_visit = to_visit
        self.lastmod = lastmod
        self.visited_links: set[str] = set()
        self.content_hashes: set[int] = set()

        self.at_least_one_doc: bool = False
        self.last_error: str | None = None
        self.needs_retry: bool = False

        self.playwright: Playwright | None = None
        self.playwright_context: BrowserContext | None = None

    def initialize(self) -> None:
        self.stop()
        self.playwright, self.playwright_context = start_playwright()

    def stop(self) -> None:
        if self.playwright_context:
            self.playwright_context.close()
            self.playwright_context = None

        if self.playwright:
            self.playwright.stop()
            self.playwright = None


class ScrapeResult:
    doc: Document | None = None
    retry: bool = False


WEB_CONNECTOR_MAX_SCROLL_ATTEMPTS = 20
# Threshold for determining when to replace vs append iframe content
IFRAME_TEXT_LENGTH_THRESHOLD = 700
# Message indicating JavaScript is disabled, which often appears when scraping fails
JAVASCRIPT_DISABLED_MESSAGE = "You have JavaScript disabled in your browser"
# Grace period after page navigation to allow bot-detection challenges
# and SPA content rendering to complete
PAGE_RENDER_TIMEOUT_MS = 5000

# EEA: Resource types to block during scraping for performance
WEB_CONNECTOR_RESOURCE_TYPES_TO_BLOCK = [
    "image",
    "font",
    "media",
    "texttrack",
    "eventsource",
    "websocket",
    "manifest",
    "other",
]


class WEB_CONNECTOR_VALID_SETTINGS(str, Enum):
    # Given a base site, index everything under that path
    RECURSIVE = "recursive"
    # Given a URL, index only the given page
    SINGLE = "single"
    # Given a sitemap.xml URL, parse all the pages in it
    SITEMAP = "sitemap"
    # Given a file upload where every line is a URL, parse all the URLs provided
    UPLOAD = "upload"


def protected_url_check(url: str) -> None:
    """Couple considerations:
    - DNS mapping changes over time so we don't want to cache the results
    - Fetching this is assumed to be relatively fast compared to other bottlenecks like reading
      the page or embedding the contents
    - To be extra safe, all IPs associated with the URL must be global
    - This is to prevent misuse and not explicit attacks
    """
    # The web connector is only guarded at the most restrictive SSRF level; at
    # VALIDATE_LLM / DISABLED admin-configured connectors may reach private IPs.
    if not web_connector_ssrf_enforced(get_security_settings().ssrf_protection_level):
        return

    parse = urlparse(url)
    if parse.scheme != "http" and parse.scheme != "https":
        raise ValueError("URL must be of scheme https?://")

    if not parse.hostname:
        raise ValueError("URL must include a hostname")

    try:
        # This may give a large list of IP addresses for domains with extensive DNS configurations
        # such as large distributed systems of CDNs
        info = socket.getaddrinfo(parse.hostname, None)
    except socket.gaierror as e:
        raise ConnectionError(f"DNS resolution failed for {parse.hostname}: {e}")

    for address in info:
        ip = address[4][0]
        if not ipaddress.ip_address(ip).is_global:
            raise ValueError(
                f"Non-global IP address detected: {ip}, skipping page {url}. "
                f"The Web Connector is not allowed to read loopback, link-local, or private ranges"
            )


def abort_unnecessary_resources(route: Route, request: Request) -> None:
    """EEA: Block unnecessary resource types during scraping for performance."""
    if request.resource_type in WEB_CONNECTOR_RESOURCE_TYPES_TO_BLOCK:
        route.abort()
    else:
        route.continue_()


def _get_datetime_from_last_modified_header(last_modified: str) -> datetime | None:
    """Parse a Last-Modified or sitemap lastmod string into a UTC datetime."""
    formats = [
        "%a, %d %b %Y %H:%M:%S %Z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(last_modified, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            else:
                dt = dt.astimezone(timezone.utc)
            return dt
        except (ValueError, TypeError):
            pass
    return None


def _filter_urls_by_timestamp(
    urls_data: dict[str, str | None],
) -> tuple[dict[str, str | None], int, int]:
    """Filter URLs based on doc_updated_at timestamps to skip unchanged documents.

    Compares sitemap lastmod timestamps with existing document timestamps.
    URLs are included if they're new, have no timestamp, or have a changed timestamp.
    """
    if not urls_data:
        return urls_data, 0, 0

    try:
        url_list = list(urls_data.keys())
        with get_session_with_current_tenant() as db_session:
            existing_timestamps = get_documents_updated_at_batch(url_list, db_session)

        filtered_urls: dict[str, str | None] = {}
        for url, lastmod_str in urls_data.items():
            existing_timestamp = existing_timestamps.get(url)

            if existing_timestamp is None:
                filtered_urls[url] = lastmod_str
            elif lastmod_str is None:
                filtered_urls[url] = lastmod_str
            else:
                sitemap_timestamp = _get_datetime_from_last_modified_header(lastmod_str)
                if sitemap_timestamp is None:
                    filtered_urls[url] = lastmod_str
                elif sitemap_timestamp != existing_timestamp:
                    filtered_urls[url] = lastmod_str

        original_count = len(urls_data)
        filtered_count = len(filtered_urls)
        skipped_count = original_count - filtered_count

        if skipped_count > 0:
            logger.info(
                "Sitemap optimization: Filtered out %s unchanged URLs "
                "out of %s total (will scrape %s URLs)",
                skipped_count,
                original_count,
                filtered_count,
            )
        else:
            logger.info(
                "Sitemap optimization: All %s URLs are new or modified, no URLs filtered",
                original_count,
            )

        return filtered_urls, original_count, filtered_count

    except Exception as e:
        original_count = len(urls_data)
        logger.warning(
            "Failed to filter URLs by timestamp: %s. Proceeding with all %s URLs.",
            e,
            original_count,
        )
        return urls_data, original_count, original_count


def set_auth_cookies() -> dict[str, str]:
    """EEA: Return auth cookies for protected site requests."""
    cookies: dict[str, str] = {}
    if eea_global_auth.get("login") is not None:
        cookies["__ac__eea"] = eea_global_auth["login"]["__ac__eea"]
        cookies["auth_token"] = eea_global_auth["login"]["auth_token"]
    return cookies


def check_internet_connection(url: str) -> None:
    # EEA: Skip validation for protected site URLs
    if url.endswith("protected=true"):
        return

    # SSRF guard on the fetch primitive itself, so no call site can reach an
    # internal target. No-op unless SSRF protection is at its strictest level.
    protected_url_check(url)

    try:
        # Use a more realistic browser-like request
        session = requests.Session()
        session.headers.update(DEFAULT_HEADERS)

        response = session.get(url, timeout=5, allow_redirects=True)

        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        # Extract status code from the response, defaulting to -1 if response is None
        status_code = e.response.status_code if e.response is not None else -1

        # For 403 errors, we do have internet connection, but the request is blocked by the server
        # this is usually due to bot detection. Future calls (via Playwright) will usually get
        # around this.
        if status_code == 403:
            logger.warning(
                "Received 403 Forbidden for %s, will retry with browser automation", url
            )
            return

        error_msg = {
            400: "Bad Request",
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found",
            500: "Internal Server Error",
            502: "Bad Gateway",
            503: "Service Unavailable",
            504: "Gateway Timeout",
        }.get(status_code, "HTTP Error")
        raise Exception(f"{error_msg} ({status_code}) for {url} - {e}")
    except requests.exceptions.SSLError as e:
        cause = (
            e.args[0].reason
            if isinstance(e.args, tuple) and isinstance(e.args[0], MaxRetryError)
            else e.args
        )
        raise Exception(f"SSL error {str(cause)}")
    except (requests.RequestException, ValueError) as e:
        raise Exception(f"Unable to reach {url} - check your internet connection: {e}")


def is_valid_url(url: str) -> bool:
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False


def _same_site(base_url: str, candidate_url: str) -> bool:
    base, candidate = urlparse(base_url), urlparse(candidate_url)
    base_netloc = base.netloc.lower().removeprefix("www.")
    candidate_netloc = candidate.netloc.lower().removeprefix("www.")
    if base_netloc != candidate_netloc:
        return False

    base_path = (base.path or "/").rstrip("/")
    if base_path in ("", "/"):
        return True

    candidate_path = candidate.path or "/"
    if candidate_path == base_path:
        return True

    boundary = f"{base_path}/"
    return candidate_path.startswith(boundary)


def get_internal_links(
    base_url: str, url: str, soup: BeautifulSoup, should_ignore_pound: bool = True
) -> set[str]:
    internal_links = set()
    for link in cast(list[dict[str, Any]], soup.find_all("a")):
        href = cast(str | None, link.get("href"))
        if not href:
            continue

        # Account for malformed backslashes in URLs
        href = href.replace("\\", "/")

        # "#!" indicates the page is using a hashbang URL, which is a client-side routing technique
        if should_ignore_pound and "#" in href and "#!" not in href:
            href = href.split("#")[0]

        if not is_valid_url(href):
            # Relative path handling
            href = urljoin(url, href)

        if _same_site(base_url, href):
            internal_links.add(href)
    return internal_links


def extract_urls_from_sitemap(sitemap_url: str) -> dict[str, str | None]:
    """Parse a sitemap and return a dict of URL -> lastmod.

    EEA: Supports gzip sitemaps, protected-site auth, and fallback to
    ultimate_sitemap_parser via list_pages_for_site_eea().
    """
    # SSRF guard. This fetch runs in __init__, before validation, so the check
    # must live here. Placed before the try so it surfaces as the SSRF error
    # rather than a wrapped sitemap-parse failure.
    if not sitemap_url.endswith("protected=true"):
        protected_url_check(sitemap_url)

    try:
        response = requests.get(
            sitemap_url, verify=False, headers=DEFAULT_HEADERS, timeout=REQUEST_TIMEOUT_SECONDS
        )
        response.raise_for_status()

        # EEA: Handle gzip-compressed sitemaps
        if sitemap_url.endswith(".gz"):
            with gzip.GzipFile(fileobj=io.BytesIO(response.content)) as f:
                content = f.read()
        else:
            content = response.content

        urls_data: dict[str, str | None] = {}
        soup = BeautifulSoup(content, "html.parser")
        for url_tag in soup.find_all("url"):
            loc_tag = url_tag.find("loc")
            if not loc_tag or not loc_tag.text:
                continue
            lastmod_tag = url_tag.find("lastmod")
            url = _ensure_absolute_url(sitemap_url, loc_tag.text)
            urls_data[url] = lastmod_tag.text if lastmod_tag else None

        # EEA: Handle protected sitemaps
        if "protected=true" in sitemap_url:
            eea_auth = soer_login()
            eea_global_auth["login"] = eea_auth
            urls_data = list_pages_for_protected_site_eea(sitemap_url, eea_auth)

        if len(urls_data) == 0 and len(soup.find_all("urlset")) == 0:
            # the given url doesn't look like a sitemap, let's try to find one
            urls_data = list_pages_for_site(sitemap_url)

        # EEA: Fallback to ultimate_sitemap_parser
        if len(urls_data) == 0:
            urls_data = list_pages_for_site_eea(sitemap_url)

        if len(urls_data) == 0:
            raise ValueError(
                f"No URLs found in sitemap {sitemap_url}. Try using the 'single' or 'recursive' scraping options instead."
            )

        return urls_data
    except requests.RequestException as e:
        raise RuntimeError(f"Failed to fetch sitemap from {sitemap_url}: {e}")
    except ValueError as e:
        raise RuntimeError(f"Error processing sitemap {sitemap_url}: {e}")
    except Exception as e:
        raise RuntimeError(
            f"Unexpected error while processing sitemap {sitemap_url}: {e}"
        )


def _ensure_absolute_url(source_url: str, maybe_relative_url: str) -> str:
    if not urlparse(maybe_relative_url).netloc:
        return urljoin(source_url, maybe_relative_url)
    return maybe_relative_url


def _ensure_valid_url(url: str) -> str:
    if "://" not in url:
        return "https://" + url
    return url


def _read_urls_file(location: str) -> list[str]:
    with open(location, "r") as f:
        urls = [_ensure_valid_url(line.strip()) for line in f if line.strip()]
    return urls


def _handle_cookies(context: BrowserContext, url: str) -> None:
    """Handle cookies for the given URL to help with bot detection"""
    try:
        # Parse the URL to get the domain
        parsed_url = urlparse(url)
        domain = parsed_url.netloc

        # Add some common cookies that might help with bot detection
        cookies: list[dict[str, str]] = [
            {
                "name": "cookieconsent",
                "value": "accepted",
                "domain": domain,
                "path": "/",
            },
            {
                "name": "consent",
                "value": "true",
                "domain": domain,
                "path": "/",
            },
            {
                "name": "session",
                "value": "random_session_id",
                "domain": domain,
                "path": "/",
            },
        ]

        # Add cookies to the context
        for cookie in cookies:
            try:
                context.add_cookies([cookie])  # ty: ignore[invalid-argument-type]
            except Exception as e:
                logger.debug(
                    "Failed to add cookie %s for %s: %s", cookie["name"], domain, e
                )
        # EEA: Inject auth cookies for protected sites
        if eea_global_auth.get("login") is not None:
            try:
                context.add_cookies(
                    [
                        {
                            "name": "__ac__eea",
                            "value": eea_global_auth["login"]["__ac__eea"],
                            "domain": "www.eea.europa.eu",
                            "path": "/",
                        },
                        {
                            "name": "auth_token",
                            "value": eea_global_auth["login"]["auth_token"],
                            "domain": "www.eea.europa.eu",
                            "path": "/",
                        },
                    ]
                )
            except Exception as e:
                logger.debug("Failed to add EEA auth cookies: %s", e)
    except Exception:
        logger.exception(
            "Unexpected error while handling cookies for Web Connector with URL %s", url
        )


class WebConnector(LoadConnector, SlimConnector):
    MAX_RETRIES = 3

    def __init__(
        self,
        base_url: str,  # Can't change this without disrupting existing users
        web_connector_type: str = WEB_CONNECTOR_VALID_SETTINGS.RECURSIVE.value,
        mintlify_cleanup: bool = True,  # Mostly ok to apply to other websites as well
        batch_size: int = INDEX_BATCH_SIZE,
        scroll_before_scraping: bool = False,
        remove_by_selector: list[str] | None = None,
        skip_unchanged_documents: bool = False,
        timeout: int = 30000,
        **kwargs: Any,  # noqa: ARG002
    ) -> None:
        self.mintlify_cleanup = mintlify_cleanup
        self.batch_size = batch_size
        self.recursive = False
        self.scroll_before_scraping = scroll_before_scraping
        self.remove_by_selector = remove_by_selector or []
        self.timeout = timeout or 30000
        self.web_connector_type = web_connector_type
        self.skip_unchanged_documents = skip_unchanged_documents
        self.original_url_count = 0
        self.filtered_url_count = 0

        if not isinstance(self.remove_by_selector, list):
            self.remove_by_selector = []

        if web_connector_type == WEB_CONNECTOR_VALID_SETTINGS.RECURSIVE.value:
            self.recursive = True
            self.to_visit_list = [_ensure_valid_url(base_url)]
            self.lastmod: list[str | None] = [None]
            return

        elif web_connector_type == WEB_CONNECTOR_VALID_SETTINGS.SINGLE.value:
            self.to_visit_list = [_ensure_valid_url(base_url)]
            self.lastmod = [None]

        elif web_connector_type == WEB_CONNECTOR_VALID_SETTINGS.SITEMAP:
            urls_data = extract_urls_from_sitemap(_ensure_valid_url(base_url))
            # EEA: Apply timestamp-based filtering to skip unchanged documents
            if self.skip_unchanged_documents:
                urls_data, self.original_url_count, self.filtered_url_count = (
                    _filter_urls_by_timestamp(urls_data)
                )
            else:
                self.original_url_count = len(urls_data)
                self.filtered_url_count = len(urls_data)
            self.to_visit_list = list(urls_data.keys())
            self.lastmod = list(urls_data.values())

        elif web_connector_type == WEB_CONNECTOR_VALID_SETTINGS.UPLOAD:
            # Explicitly check if running in multi-tenant mode to prevent potential security risks
            if MULTI_TENANT:
                raise ValueError(
                    "Upload input for web connector is not supported in cloud environments"
                )

            logger.warning(
                "This is not a UI supported Web Connector flow, are you sure you want to do this?"
            )
            self.to_visit_list = _read_urls_file(base_url)
            self.lastmod = [None] * len(self.to_visit_list)

        else:
            raise ValueError(
                "Invalid Web Connector Config, must choose a valid type between: "
            )

    def load_credentials(self, credentials: dict[str, Any]) -> dict[str, Any] | None:
        if credentials:
            logger.warning("Unexpected credentials provided for Web Connector")
        return None

    def _do_scrape(
        self,
        index: int,
        initial_url: str,
        lastmod: str | None,
        session_ctx: ScrapeSessionContext,
        slim: bool = False,
    ) -> ScrapeResult:
        """Returns a ScrapeResult object with a doc and retry flag.

        When slim=True, skips scroll, PDF content download, and content extraction.
        The bot-detection render wait (5s) fires on CF/403 responses regardless of slim.
        networkidle is always awaited so JS-rendered links are discovered correctly.
        """

        if session_ctx.playwright is None:
            raise RuntimeError("scrape_context.playwright is None")

        if session_ctx.playwright_context is None:
            raise RuntimeError("scrape_context.playwright_context is None")

        result = ScrapeResult()

        # Handle cookies for the URL
        _handle_cookies(session_ctx.playwright_context, initial_url)

        # First do a HEAD request to check content type without downloading the entire content
        auth_cookies = set_auth_cookies()
        head_response = requests.head(
            initial_url,
            headers=DEFAULT_HEADERS,
            cookies=auth_cookies,
            allow_redirects=True,
            timeout=(5, 10),
        )
        # EEA: For protected file downloads, use GET with streaming
        if eea_global_auth.get("login") is not None and "@@download/file" in initial_url:
            head_response = requests.get(
                initial_url,
                headers=DEFAULT_HEADERS,
                cookies=auth_cookies,
                allow_redirects=True,
                stream=True,
            )
        content_type = head_response.headers.get("content-type")
        is_pdf = is_pdf_resource(initial_url, content_type)

        # EEA: Handle non-PDF protected file downloads (@@download/file)
        if not is_pdf and "@@download/file" in initial_url:
            response = requests.get(
                initial_url, headers=DEFAULT_HEADERS, cookies=auth_cookies
            )
            page_text = response.text
            last_modified = response.headers.get("Last-Modified") or lastmod
            result.doc = Document(
                id=initial_url,
                sections=[TextSection(link=initial_url, text=page_text)],
                source=DocumentSource.WEB,
                semantic_identifier=initial_url.split("/")[
                    -3 if "@@download/file" in initial_url else -1
                ],
                metadata={},
                doc_updated_at=(
                    _get_datetime_from_last_modified_header(last_modified)
                    if last_modified
                    else None
                ),
            )
            return result

        if is_pdf or initial_url.lower().endswith(".pdf"):
            if slim:
                result.doc = Document(
                    id=initial_url,
                    sections=[],
                    source=DocumentSource.WEB,
                    semantic_identifier=initial_url,
                    metadata={},
                )
                return result

            response = requests.get(
                initial_url,
                headers=DEFAULT_HEADERS,
                cookies=auth_cookies,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            page_text, metadata, images = read_pdf_file(
                file=io.BytesIO(response.content)
            )
            last_modified = response.headers.get("Last-Modified") or lastmod
            title = metadata.get("Title") or metadata.get("title")

            result.doc = Document(
                id=initial_url,
                sections=[TextSection(link=initial_url, text=page_text)],
                source=DocumentSource.WEB,
                semantic_identifier=title
                or initial_url.split("/")[
                    -3 if "@@download/file" in initial_url else -1
                ],
                metadata=metadata,
                doc_updated_at=(
                    _get_datetime_from_last_modified_header(last_modified)
                    if last_modified
                    else None
                ),
            )

            return result

        page = session_ctx.playwright_context.new_page()
        # EEA: Block unnecessary resources for performance
        page.route("**/*", abort_unnecessary_resources)
        try:
            # Use "commit" instead of "domcontentloaded" to avoid hanging on bot-detection pages
            # that may never fire domcontentloaded. "commit" waits only for navigation to be
            # committed (response received), then we add a short wait for initial rendering.
            page_response = page.goto(
                initial_url,
                timeout=self.timeout,
                wait_until="commit",  # Wait for navigation to commit
            )

            # Bot-detection JS challenges (CloudFlare, Imperva, etc.) need a moment
            # to start network activity after commit before networkidle is meaningful.
            # We detect this via the cf-ray header (CloudFlare) or a 403 response,
            # which is the common entry point for JS-challenge-based bot detection.
            is_bot_challenge = page_response is not None and (
                page_response.header_value("cf-ray") is not None
                or page_response.status == 403
            )
            if is_bot_challenge:
                page.wait_for_timeout(PAGE_RENDER_TIMEOUT_MS)

            # Wait for network activity to settle (handles SPAs, CF challenges, etc.)
            try:
                page.wait_for_load_state("networkidle", timeout=PAGE_RENDER_TIMEOUT_MS)
            except TimeoutError:
                pass

            # EEA: Remove images from DOM before content extraction
            page.evaluate("""
                () => {
                    const images = document.querySelectorAll('img');
                    images.forEach(img => img.remove());
                }
            """)

            try:
                response_last_modified = (
                    page_response.header_value("Last-Modified")
                    if page_response
                    else None
                )
            except Exception:
                response_last_modified = None

            last_modified = response_last_modified or lastmod
            final_url = page.url
            if final_url != initial_url:
                protected_url_check(final_url)
                initial_url = final_url
                if initial_url in session_ctx.visited_links:
                    logger.info(
                        "%s: %s redirected to %s - already indexed",
                        index,
                        initial_url,
                        final_url,
                    )
                    page.close()
                    return result

                logger.info("%s: %s redirected to %s", index, initial_url, final_url)
                session_ctx.visited_links.add(initial_url)

            # If we got here, the request was successful
            if not slim and self.scroll_before_scraping:
                try:
                    # document.body can be null for non-HTML responses,
                    # transient frame-nav states, or pages rendered without
                    # a body (e.g. pure XML, some SPAs mid-navigation). That
                    # surfaces as "Page.evaluate: TypeError: Cannot read
                    # properties of null (reading 'scrollHeight')"
                    # (ONYX-BACKEND-H6G5). Skip auto-scroll in that case and
                    # fall back to whatever content the initial load gave us.
                    scroll_attempts = 0
                    previous_height = page.evaluate("document.body.scrollHeight")
                    while scroll_attempts < WEB_CONNECTOR_MAX_SCROLL_ATTEMPTS:
                        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        # Wait for content to load, but catch timeout if page never reaches networkidle
                        # (e.g., CloudFlare protection keeps making requests)
                        try:
                            page.wait_for_load_state(
                                "networkidle", timeout=PAGE_RENDER_TIMEOUT_MS
                            )
                        except TimeoutError:
                            # If networkidle times out, just give it a moment for content to render
                            time.sleep(1)
                        time.sleep(0.5)  # let javascript run

                        new_height = page.evaluate("document.body.scrollHeight")
                        if new_height == previous_height:
                            break  # Stop scrolling when no more content is loaded
                        previous_height = new_height
                        scroll_attempts += 1
                except Exception as scroll_err:
                    logger.warning(
                        "%s: auto-scroll skipped for %s: %s",
                        index,
                        initial_url,
                        scroll_err,
                    )

            content = page.content()
            soup = BeautifulSoup(content, "html.parser")

            # EEA: Remove elements matching CSS selectors before indexing
            remove_by_selector(soup, self.remove_by_selector)

            if self.recursive:
                internal_links = get_internal_links(
                    session_ctx.base_url, initial_url, soup
                )
                for link in internal_links:
                    if link not in session_ctx.visited_links:
                        session_ctx.to_visit.append(link)
                        session_ctx.lastmod.append(None)

            if page_response and str(page_response.status)[0] in ("4", "5"):
                session_ctx.last_error = f"Skipped indexing {initial_url} due to HTTP {page_response.status} response"
                logger.info(session_ctx.last_error)
                result.retry = True
                return result

            if slim:
                result.doc = Document(
                    id=initial_url,
                    sections=[],
                    source=DocumentSource.WEB,
                    semantic_identifier=initial_url,
                    metadata={},
                )
                return result

            # after this point, we don't need the caller to retry
            parsed_html = web_html_cleanup(soup, self.mintlify_cleanup)

            """For websites containing iframes that need to be scraped,
            the code below can extract text from within these iframes.
            """
            logger.debug(
                "%s: Length of cleaned text %s", index, len(parsed_html.cleaned_text)
            )
            if JAVASCRIPT_DISABLED_MESSAGE in parsed_html.cleaned_text:
                iframe_count = page.frame_locator("iframe").locator("html").count()
                if iframe_count > 0:
                    iframe_texts = (
                        page.frame_locator("iframe").locator("html").all_inner_texts()
                    )
                    document_text = "\n".join(iframe_texts)
                    """ 700 is the threshold value for the length of the text extracted
                    from the iframe based on the issue faced """
                    if len(parsed_html.cleaned_text) < IFRAME_TEXT_LENGTH_THRESHOLD:
                        parsed_html.cleaned_text = document_text
                    else:
                        parsed_html.cleaned_text += "\n" + document_text

            # Sometimes pages with #! will serve duplicate content
            # There are also just other ways this can happen
            hashed_text = hash((parsed_html.title, parsed_html.cleaned_text))
            if hashed_text in session_ctx.content_hashes:
                logger.info(
                    "%s: Skipping duplicate title + content for %s", index, initial_url
                )
                return result

            session_ctx.content_hashes.add(hashed_text)

            result.doc = Document(
                id=initial_url,
                sections=[TextSection(link=initial_url, text=parsed_html.cleaned_text)],
                source=DocumentSource.WEB,
                semantic_identifier=parsed_html.title or initial_url,
                metadata={},
                doc_updated_at=(
                    _get_datetime_from_last_modified_header(last_modified)
                    if last_modified
                    else None
                ),
            )
        finally:
            page.close()

        return result

    def load_from_state(self, slim: bool = False) -> GenerateDocumentsOutput:
        """Traverses through all pages found on the website and converts them into
        documents.

        When slim=True, yields SlimDocument objects (URL id only, no content).
        Playwright is used in all modes — slim skips content extraction only.
        """

        # EEA: Check if URLs were filtered vs never existed
        if self.original_url_count > 0 and self.filtered_url_count == 0:
            logger.info(
                "No URLs to visit after filtering. All %s "
                "documents are up-to-date. Skipping connector execution.",
                self.original_url_count,
            )
            return

        if not self.to_visit_list:
            raise ValueError("No URLs to visit")

        base_url = self.to_visit_list[0]  # For the recursive case
        check_internet_connection(base_url)  # make sure we can connect to the base url

        session_ctx = ScrapeSessionContext(base_url, self.to_visit_list, self.lastmod)
        session_ctx.initialize()

        batch: list[Document | SlimDocument | HierarchyNode] = []

        while session_ctx.to_visit:
            initial_url = session_ctx.to_visit.pop()
            lastmod = session_ctx.lastmod.pop() if session_ctx.lastmod else None
            if initial_url in session_ctx.visited_links:
                continue
            session_ctx.visited_links.add(initial_url)

            try:
                protected_url_check(initial_url)
            except Exception as e:
                session_ctx.last_error = f"Invalid URL {initial_url} due to {e}"
                logger.warning(session_ctx.last_error)
                continue

            index = len(session_ctx.visited_links)
            logger.info(
                "%s: %s %s", index, "Slim-visiting" if slim else "Visiting", initial_url
            )

            # Add retry mechanism with exponential backoff
            retry_count = 0

            while retry_count < self.MAX_RETRIES:
                if retry_count > 0:
                    # Add a random delay between retries (exponential backoff)
                    delay = min(2**retry_count + random.uniform(0, 1), 10)
                    logger.info(
                        "Retry %s/%s for %s after %ss delay",
                        retry_count,
                        self.MAX_RETRIES,
                        initial_url,
                        format(delay, ".2f"),
                    )
                    time.sleep(delay)

                try:
                    result = self._do_scrape(
                        index, initial_url, lastmod, session_ctx, slim=slim
                    )
                    if result.retry:
                        continue

                    if result.doc:
                        batch.append(
                            SlimDocument(id=result.doc.id) if slim else result.doc
                        )
                except Exception as e:
                    session_ctx.last_error = f"Failed to fetch '{initial_url}': {e}"
                    logger.exception(session_ctx.last_error)
                    session_ctx.initialize()
                    continue
                finally:
                    retry_count += 1

                break  # success / don't retry

            if len(batch) >= self.batch_size:
                session_ctx.initialize()
                session_ctx.at_least_one_doc = True
                yield batch  # ty: ignore[invalid-yield]
                batch = []

        if batch:
            session_ctx.stop()
            session_ctx.at_least_one_doc = True
            yield batch  # ty: ignore[invalid-yield]

        if not session_ctx.at_least_one_doc:
            if session_ctx.last_error:
                raise RuntimeError(session_ctx.last_error)
            raise RuntimeError("No valid pages found.")

        session_ctx.stop()

    @override
    def retrieve_all_slim_docs(
        self,
        start: SecondsSinceUnixEpoch | None = None,
        end: SecondsSinceUnixEpoch | None = None,
        callback: IndexingHeartbeatInterface | None = None,
    ) -> GenerateSlimDocumentOutput:
        """Yields SlimDocuments for all pages reachable from the configured URLs.

        Uses the same Playwright crawl as full indexing but skips content extraction,
        scroll, and PDF downloads. The 5s render wait fires only on bot-detection
        responses (CloudFlare cf-ray header or HTTP 403).
        The start/end parameters are ignored — WEB connector has no incremental path.
        """
        yield from self.load_from_state(slim=True)  # ty: ignore[invalid-yield]

    def validate_connector_settings(self) -> None:
        # EEA: Check if URLs were filtered vs never existed
        if self.original_url_count > 0 and self.filtered_url_count == 0:
            logger.info(
                "Sitemap connector has no URLs to visit after filtering. "
                "All %s documents are up-to-date.",
                self.original_url_count,
            )
            return None

        # Make sure we have at least one valid URL to check
        if not self.to_visit_list:
            raise ConnectorValidationError(
                "No URL configured. Please provide at least one valid URL."
            )

        # Recursive/sitemap defer page fetches to index time; skip the connectivity
        # probe for them.
        if (
            self.web_connector_type == WEB_CONNECTOR_VALID_SETTINGS.SITEMAP.value
            or self.web_connector_type == WEB_CONNECTOR_VALID_SETTINGS.RECURSIVE.value
        ):
            return None

        # We'll just test the first URL for connectivity and correctness
        test_url = self.to_visit_list[0]

        # SSRF check runs for every connector type so an internal target is
        # rejected at creation rather than at index time.
        try:
            protected_url_check(test_url)
        except ValueError as e:
            raise ConnectorValidationError(
                f"Protected URL check failed for '{test_url}': {e}"
            )
        except ConnectionError as e:
            # Typically DNS or other network issues
            raise ConnectorValidationError(str(e))

        # Make a quick request to see if we get a valid response. This re-runs the
        # SSRF check internally (intentional, cheap defense-in-depth).
        try:
            check_internet_connection(test_url)
        except Exception as e:
            err_str = str(e)
            if "401" in err_str:
                raise CredentialExpiredError(
                    f"Unauthorized access to '{test_url}': {e}"
                )
            elif "403" in err_str:
                raise InsufficientPermissionsError(
                    f"Forbidden access to '{test_url}': {e}"
                )
            elif "404" in err_str:
                raise ConnectorValidationError(f"Page not found for '{test_url}': {e}")
            elif "Max retries exceeded" in err_str and "NameResolutionError" in err_str:
                raise ConnectorValidationError(
                    f"Unable to resolve hostname for '{test_url}'. Please check the URL and your internet connection."
                )
            else:
                # Could be a 5xx or another error, treat as unexpected
                raise UnexpectedValidationError(
                    f"Unexpected error validating '{test_url}': {e}"
                )


if __name__ == "__main__":
    connector = WebConnector("https://docs.onyx.app/")
    document_batches = connector.load_from_state()
    print(next(document_batches))
