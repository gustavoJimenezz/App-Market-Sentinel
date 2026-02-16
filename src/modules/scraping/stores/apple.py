import structlog

from src.modules.scraping.base import BaseScraper
from src.modules.scraping.client import HTTPClient
from src.modules.scraping.parsers import AppMetadataParser, PriceParser, ReviewParser
from src.modules.scraping.schemas import ScrapeResult

logger = structlog.get_logger()

_APP_METADATA_PARSER = AppMetadataParser(
    name_selector="h1.product-header__title",
    developer_selector="h2.product-header__identity a",
    description_selector="section.section--description .we-truncate p",
    icon_selector="picture.product-hero__media source",
)

_PRICE_PARSER = PriceParser(
    price_selector="li.inline-list__item--bulleted:first-child",
)

_REVIEW_PARSER = ReviewParser(
    container_selector=".we-customer-review",
    id_attr="data-review-id",
    rating_selector="figure.we-star-rating",
    title_selector="h3.we-customer-review__title",
    content_selector="p.we-customer-review__body",
    author_selector="span.we-customer-review__user",
    date_selector="time.we-customer-review__date",
)


class AppleStoreScraper(BaseScraper):
    BASE_URL = "https://apps.apple.com/us/app"

    def __init__(self, client: HTTPClient) -> None:
        super().__init__(client)

    def build_url(self, bundle_id: str) -> str:
        return f"{self.BASE_URL}/id{bundle_id}"

    async def scrape(self, bundle_id: str) -> ScrapeResult:
        url = self.build_url(bundle_id)
        log = logger.bind(url=url, bundle_id=bundle_id)

        try:
            response = await self.client.get(url)
            html = response.text

            app = _APP_METADATA_PARSER.parse(html, bundle_id)
            price = _PRICE_PARSER.parse(html)
            reviews = _REVIEW_PARSER.parse(html)

            log.info(
                "apple_scrape_ok",
                has_app=app is not None,
                has_price=price is not None,
                review_count=len(reviews),
            )

            return ScrapeResult(
                url=url,
                app=app,
                price=price,
                reviews=reviews,
                success=True,
            )
        except Exception as exc:
            log.error("apple_scrape_error", error=str(exc))
            return ScrapeResult(url=url, success=False, error=str(exc))
