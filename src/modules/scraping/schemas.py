"""Pydantic schemas for scraped data with validation & normalisation."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, field_validator

from src.modules.scraping.normalizers import ensure_timezone_aware, normalize_currency

# --- DB column limits ---
_MAX_NAME = 255
_MAX_BUNDLE_ID = 255
_MAX_DEVELOPER = 255
_MAX_ICON_URL = 512
_MAX_TITLE = 500
_MAX_AUTHOR = 255
_MAX_REVIEW_ID = 255
_MAX_CURRENCY = 3
_MAX_REGION = 5
_MAX_PRICE = Decimal("99999999.99")


# --- Helpers ---
def _strip_or_none(v: str | None) -> str | None:
    if v is None:
        return None
    stripped = v.strip()
    return stripped if stripped else None


def _validate_max_length(v: str, max_len: int, field_name: str) -> str:
    if len(v) > max_len:
        msg = f"{field_name} exceeds max length of {max_len}"
        raise ValueError(msg)
    return v


class ScrapedApp(BaseModel):
    name: str
    bundle_id: str
    developer_name: str | None = None
    description: str | None = None
    icon_url: str | None = None

    @field_validator("name", "bundle_id", mode="before")
    @classmethod
    def strip_and_require(cls, v: str, info) -> str:
        if not isinstance(v, str):
            return v
        stripped = v.strip()
        if not stripped:
            raise ValueError(f"{info.field_name} cannot be empty")
        return stripped

    @field_validator("name", mode="after")
    @classmethod
    def name_max_length(cls, v: str) -> str:
        return _validate_max_length(v, _MAX_NAME, "name")

    @field_validator("bundle_id", mode="after")
    @classmethod
    def bundle_id_max_length(cls, v: str) -> str:
        return _validate_max_length(v, _MAX_BUNDLE_ID, "bundle_id")

    @field_validator("developer_name", mode="before")
    @classmethod
    def developer_name_strip(cls, v: str | None) -> str | None:
        result = _strip_or_none(v)
        if result is not None:
            return _validate_max_length(result, _MAX_DEVELOPER, "developer_name")
        return None

    @field_validator("icon_url", mode="before")
    @classmethod
    def icon_url_max_length(cls, v: str | None) -> str | None:
        result = _strip_or_none(v)
        if result is not None:
            return _validate_max_length(result, _MAX_ICON_URL, "icon_url")
        return None


class ScrapedPrice(BaseModel):
    price: Decimal
    currency: str
    region: str
    timestamp: datetime

    @field_validator("price", mode="after")
    @classmethod
    def price_range(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError("Price cannot be negative")
        if v > _MAX_PRICE:
            raise ValueError(f"Price exceeds maximum of {_MAX_PRICE}")
        return v

    @field_validator("currency", mode="before")
    @classmethod
    def currency_normalize(cls, v: str) -> str:
        if not isinstance(v, str):
            return v
        return normalize_currency(v)

    @field_validator("region", mode="before")
    @classmethod
    def region_normalize(cls, v: str) -> str:
        if not isinstance(v, str):
            return v
        upper = v.strip().upper()
        return _validate_max_length(upper, _MAX_REGION, "region")

    @field_validator("timestamp", mode="after")
    @classmethod
    def timestamp_tz(cls, v: datetime) -> datetime:
        return ensure_timezone_aware(v)


class ScrapedReview(BaseModel):
    external_review_id: str
    rating: int
    title: str | None = None
    content: str | None = None
    author_name: str | None = None
    review_date: datetime | None = None

    @field_validator("external_review_id", mode="before")
    @classmethod
    def review_id_strip_require(cls, v: str) -> str:
        if not isinstance(v, str):
            return v
        stripped = v.strip()
        if not stripped:
            raise ValueError("external_review_id cannot be empty")
        return _validate_max_length(stripped, _MAX_REVIEW_ID, "external_review_id")

    @field_validator("rating", mode="after")
    @classmethod
    def rating_range(cls, v: int) -> int:
        if v < 1 or v > 5:
            raise ValueError("Rating must be between 1 and 5")
        return v

    @field_validator("title", mode="before")
    @classmethod
    def title_strip(cls, v: str | None) -> str | None:
        result = _strip_or_none(v)
        if result is not None:
            return _validate_max_length(result, _MAX_TITLE, "title")
        return None

    @field_validator("author_name", mode="before")
    @classmethod
    def author_name_strip(cls, v: str | None) -> str | None:
        result = _strip_or_none(v)
        if result is not None:
            return _validate_max_length(result, _MAX_AUTHOR, "author_name")
        return None

    @field_validator("review_date", mode="after")
    @classmethod
    def review_date_tz(cls, v: datetime | None) -> datetime | None:
        if v is None:
            return None
        return ensure_timezone_aware(v)


class ScrapeResult(BaseModel):
    url: str
    app: ScrapedApp | None = None
    price: ScrapedPrice | None = None
    reviews: list[ScrapedReview] = []
    success: bool = True
    error: str | None = None

    @field_validator("url", mode="before")
    @classmethod
    def url_strip_require(cls, v: str) -> str:
        if not isinstance(v, str):
            return v
        stripped = v.strip()
        if not stripped:
            raise ValueError("url cannot be empty")
        return stripped
