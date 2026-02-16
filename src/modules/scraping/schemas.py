from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class ScrapedApp(BaseModel):
    name: str
    bundle_id: str
    developer_name: str | None = None
    description: str | None = None
    icon_url: str | None = None


class ScrapedPrice(BaseModel):
    price: Decimal
    currency: str
    region: str
    timestamp: datetime


class ScrapedReview(BaseModel):
    external_review_id: str
    rating: int
    title: str | None = None
    content: str | None = None
    author_name: str | None = None
    review_date: datetime | None = None


class ScrapeResult(BaseModel):
    url: str
    app: ScrapedApp | None = None
    price: ScrapedPrice | None = None
    reviews: list[ScrapedReview] = []
    success: bool = True
    error: str | None = None
