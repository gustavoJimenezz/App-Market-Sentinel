import re
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation

from bs4 import BeautifulSoup, Tag

from src.modules.scraping.schemas import ScrapedApp, ScrapedPrice, ScrapedReview


class HTMLParser:
    @staticmethod
    def parse_html(html: str) -> BeautifulSoup:
        return BeautifulSoup(html, "html.parser")

    @staticmethod
    def extract_text(element: Tag | None) -> str | None:
        if element is None:
            return None
        text = element.get_text(strip=True)
        return text if text else None

    @staticmethod
    def extract_attr(element: Tag | None, attr: str) -> str | None:
        if element is None:
            return None
        value = element.get(attr)
        if isinstance(value, list):
            return value[0] if value else None
        return value


class AppMetadataParser(HTMLParser):
    def __init__(
        self,
        *,
        name_selector: str,
        developer_selector: str,
        description_selector: str,
        icon_selector: str,
    ) -> None:
        self.name_selector = name_selector
        self.developer_selector = developer_selector
        self.description_selector = description_selector
        self.icon_selector = icon_selector

    def parse(self, html: str, bundle_id: str) -> ScrapedApp | None:
        soup = self.parse_html(html)

        name = self.extract_text(soup.select_one(self.name_selector))
        if not name:
            return None

        return ScrapedApp(
            name=name,
            bundle_id=bundle_id,
            developer_name=self.extract_text(soup.select_one(self.developer_selector)),
            description=self.extract_text(soup.select_one(self.description_selector)),
            icon_url=self.extract_attr(soup.select_one(self.icon_selector), "src"),
        )


class PriceParser(HTMLParser):
    _CURRENCY_SYMBOLS = re.compile(r"[^\d.,]")

    def __init__(self, *, price_selector: str) -> None:
        self.price_selector = price_selector

    def parse(
        self, html: str, *, currency: str = "USD", region: str = "US"
    ) -> ScrapedPrice | None:
        soup = self.parse_html(html)
        raw = self.extract_text(soup.select_one(self.price_selector))
        if not raw:
            return None

        if raw.lower() == "free":
            price_value = Decimal("0.00")
        else:
            cleaned = self._CURRENCY_SYMBOLS.sub("", raw).replace(",", ".")
            try:
                price_value = Decimal(cleaned)
            except InvalidOperation:
                return None

        return ScrapedPrice(
            price=price_value,
            currency=currency,
            region=region,
            timestamp=datetime.now(UTC),
        )


class ReviewParser(HTMLParser):
    def __init__(
        self,
        *,
        container_selector: str,
        id_attr: str = "data-review-id",
        rating_selector: str,
        title_selector: str,
        content_selector: str,
        author_selector: str,
        date_selector: str,
    ) -> None:
        self.container_selector = container_selector
        self.id_attr = id_attr
        self.rating_selector = rating_selector
        self.title_selector = title_selector
        self.content_selector = content_selector
        self.author_selector = author_selector
        self.date_selector = date_selector

    def parse(self, html: str) -> list[ScrapedReview]:
        soup = self.parse_html(html)
        containers = soup.select(self.container_selector)
        reviews: list[ScrapedReview] = []

        for container in containers:
            review_id = container.get(self.id_attr)
            if not review_id:
                continue
            if isinstance(review_id, list):
                review_id = review_id[0]

            rating_el = container.select_one(self.rating_selector)
            rating_text = self.extract_attr(
                rating_el, "aria-label"
            ) or self.extract_text(rating_el)
            rating = self._parse_rating(rating_text)
            if rating is None:
                continue

            date_text = self.extract_text(container.select_one(self.date_selector))
            review_date = self._parse_date(date_text)

            reviews.append(
                ScrapedReview(
                    external_review_id=str(review_id),
                    rating=rating,
                    title=self.extract_text(container.select_one(self.title_selector)),
                    content=self.extract_text(
                        container.select_one(self.content_selector)
                    ),
                    author_name=self.extract_text(
                        container.select_one(self.author_selector)
                    ),
                    review_date=review_date,
                )
            )

        return reviews

    @staticmethod
    def _parse_rating(text: str | None) -> int | None:
        if not text:
            return None
        match = re.search(r"(\d)", text)
        return int(match.group(1)) if match else None

    @staticmethod
    def _parse_date(text: str | None) -> datetime | None:
        if not text:
            return None
        for fmt in ("%b %d, %Y", "%B %d, %Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(text, fmt).replace(tzinfo=UTC)
            except ValueError:
                continue
        return None
