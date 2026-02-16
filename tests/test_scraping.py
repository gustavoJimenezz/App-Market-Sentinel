import asyncio
from decimal import Decimal
from unittest.mock import AsyncMock

import httpx
import pytest

from src.modules.scraping.client import HTTPClient, RateLimitError
from src.modules.scraping.parsers import (
    AppMetadataParser,
    PriceParser,
    ReviewParser,
)
from src.modules.scraping.schemas import ScrapeResult
from src.modules.scraping.stores.apple import AppleStoreScraper

# --- HTTP Client tests ---


async def test_http_client_user_agent_rotation():
    """User-Agent headers should rotate across requests."""
    agents_seen: set[str] = set()

    async with HTTPClient() as client:
        for _ in range(20):
            headers = client._build_headers()
            agents_seen.add(headers["User-Agent"])

    assert len(agents_seen) > 1


async def test_http_client_retries_on_timeout():
    """Client should retry on timeout exceptions."""
    req = httpx.Request("GET", "http://test")
    mock_response = httpx.Response(200, text="ok", request=req)
    call_count = 0

    async def mock_get(url, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise httpx.TimeoutException("timeout")
        return mock_response

    async with HTTPClient() as client:
        client._client = AsyncMock()
        client._client.get = mock_get

        response = await client._get_with_retry(
            "http://test.com",
            max_retries=5,
            min_wait=0.01,
            max_wait=0.02,
        )

    assert response.status_code == 200
    assert call_count == 3


async def test_http_client_handles_429():
    """Client should raise RateLimitError on 429."""
    response_429 = httpx.Response(
        429,
        headers={"Retry-After": "5"},
        request=httpx.Request("GET", "http://test"),
    )

    async with HTTPClient() as client:
        client._client = AsyncMock()
        client._client.get = AsyncMock(return_value=response_429)

        with pytest.raises(RateLimitError) as exc_info:
            await client._get_with_retry(
                "http://test.com",
                max_retries=1,
                min_wait=0.01,
                max_wait=0.02,
            )

        assert exc_info.value.retry_after == 5.0


# --- Parser tests ---

# fmt: off
APPLE_HTML_FIXTURE = (
    "<html><body>"
    '<h1 class="product-header__title">Test App</h1>'
    '<h2 class="product-header__identity">'
    '<a href="#">Test Developer</a></h2>'
    '<section class="section--description">'
    '<div class="we-truncate">'
    "<p>A great app for testing.</p>"
    "</div></section>"
    '<picture class="product-hero__media">'
    '<source src="https://example.com/icon.png">'
    "</picture>"
    '<li class="inline-list__item--bulleted">$4.99</li>'
    '<div class="we-customer-review" data-review-id="rev-001">'
    '<figure class="we-star-rating" aria-label="4 out of 5">'
    "</figure>"
    '<h3 class="we-customer-review__title">Great app!</h3>'
    '<p class="we-customer-review__body">Works perfectly.</p>'
    '<span class="we-customer-review__user">John Doe</span>'
    '<time class="we-customer-review__date">Jan 15, 2025</time>'
    "</div>"
    '<div class="we-customer-review" data-review-id="rev-002">'
    '<figure class="we-star-rating" aria-label="2 out of 5">'
    "</figure>"
    '<h3 class="we-customer-review__title">Needs work</h3>'
    '<p class="we-customer-review__body">Some bugs.</p>'
    '<span class="we-customer-review__user">Jane Smith</span>'
    '<time class="we-customer-review__date">Feb 20, 2025</time>'
    "</div>"
    "</body></html>"
)
# fmt: on


async def test_app_metadata_parser():
    parser = AppMetadataParser(
        name_selector="h1.product-header__title",
        developer_selector="h2.product-header__identity a",
        description_selector=("section.section--description .we-truncate p"),
        icon_selector="picture.product-hero__media source",
    )
    result = parser.parse(APPLE_HTML_FIXTURE, "com.test.app")

    assert result is not None
    assert result.name == "Test App"
    assert result.bundle_id == "com.test.app"
    assert result.developer_name == "Test Developer"
    assert result.description == "A great app for testing."
    assert result.icon_url == "https://example.com/icon.png"


async def test_price_parser():
    parser = PriceParser(
        price_selector="li.inline-list__item--bulleted",
    )
    result = parser.parse(APPLE_HTML_FIXTURE)

    assert result is not None
    assert result.price == Decimal("4.99")
    assert result.currency == "USD"
    assert result.region == "US"


async def test_price_parser_free():
    html = '<html><li class="inline-list__item--bulleted">Free</li></html>'
    parser = PriceParser(
        price_selector="li.inline-list__item--bulleted:first-child",
    )
    result = parser.parse(html)

    assert result is not None
    assert result.price == 0


async def test_review_parser():
    parser = ReviewParser(
        container_selector=".we-customer-review",
        id_attr="data-review-id",
        rating_selector="figure.we-star-rating",
        title_selector="h3.we-customer-review__title",
        content_selector="p.we-customer-review__body",
        author_selector="span.we-customer-review__user",
        date_selector="time.we-customer-review__date",
    )
    reviews = parser.parse(APPLE_HTML_FIXTURE)

    assert len(reviews) == 2
    assert reviews[0].external_review_id == "rev-001"
    assert reviews[0].rating == 4
    assert reviews[0].title == "Great app!"
    assert reviews[0].content == "Works perfectly."
    assert reviews[0].author_name == "John Doe"

    assert reviews[1].external_review_id == "rev-002"
    assert reviews[1].rating == 2


# --- Apple scraper tests ---


async def test_apple_scraper_handles_error():
    """Scraper returns ScrapeResult(success=False) on error."""
    client = AsyncMock(spec=HTTPClient)
    client.get = AsyncMock(
        side_effect=httpx.HTTPStatusError(
            "Not Found",
            request=httpx.Request("GET", "http://test"),
            response=httpx.Response(404),
        )
    )

    scraper = AppleStoreScraper(client)
    result = await scraper.scrape("com.test.app")

    assert isinstance(result, ScrapeResult)
    assert result.success is False
    assert result.error is not None


async def test_scrape_batch_concurrency():
    """Semaphore should limit concurrency in scrape_batch."""
    max_concurrent = 0
    current_concurrent = 0

    client = AsyncMock(spec=HTTPClient)
    scraper = AppleStoreScraper(client)

    async def mock_scrape(bundle_id: str) -> ScrapeResult:
        nonlocal max_concurrent, current_concurrent
        current_concurrent += 1
        max_concurrent = max(max_concurrent, current_concurrent)
        await asyncio.sleep(0.01)
        current_concurrent -= 1
        return ScrapeResult(url=f"http://test/{bundle_id}", success=True)

    scraper.scrape = mock_scrape  # type: ignore[assignment]

    bundle_ids = [f"app-{i}" for i in range(20)]
    results = await scraper.scrape_batch(bundle_ids, concurrency=3)

    assert len(results) == 20
    assert max_concurrent <= 3
