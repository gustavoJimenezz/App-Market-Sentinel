"""TDD tests for the Data Quality Firewall (Ticket 4).

Tests are organised by normaliser function and then by schema.
"""

from datetime import UTC, datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from src.modules.scraping.normalizers import ensure_timezone_aware, normalize_currency
from src.modules.scraping.schemas import (
    ScrapedApp,
    ScrapedPrice,
    ScrapedReview,
    ScrapeResult,
)


# ---------------------------------------------------------------------------
# TestNormalizeCurrency
# ---------------------------------------------------------------------------
class TestNormalizeCurrency:
    def test_lowercase_to_upper(self):
        assert normalize_currency("usd") == "USD"

    def test_dollar_sign(self):
        assert normalize_currency("$") == "USD"

    def test_euro_sign(self):
        assert normalize_currency("€") == "EUR"

    def test_pound_sign(self):
        assert normalize_currency("£") == "GBP"

    def test_yen_sign(self):
        assert normalize_currency("¥") == "JPY"

    def test_invalid_raises(self):
        with pytest.raises(ValueError, match="Unknown currency"):
            normalize_currency("XYZ")

    def test_whitespace_stripped(self):
        assert normalize_currency("  eur  ") == "EUR"

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="empty"):
            normalize_currency("   ")


# ---------------------------------------------------------------------------
# TestEnsureTimezoneAware
# ---------------------------------------------------------------------------
class TestEnsureTimezoneAware:
    def test_naive_gets_utc(self):
        naive = datetime(2025, 1, 1, 12, 0, 0)
        result = ensure_timezone_aware(naive)
        assert result.tzinfo is UTC

    def test_aware_unchanged(self):
        aware = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        result = ensure_timezone_aware(aware)
        assert result is aware

    def test_non_utc_preserved(self):
        eastern = timezone(offset=__import__("datetime").timedelta(hours=-5))
        aware = datetime(2025, 1, 1, 12, 0, 0, tzinfo=eastern)
        result = ensure_timezone_aware(aware)
        assert result.tzinfo is eastern


# ---------------------------------------------------------------------------
# TestScrapedAppValidation
# ---------------------------------------------------------------------------
class TestScrapedAppValidation:
    def _valid(self, **overrides) -> dict:
        base = {"name": "My App", "bundle_id": "com.example.app"}
        base.update(overrides)
        return base

    def test_valid_minimal(self):
        app = ScrapedApp(**self._valid())
        assert app.name == "My App"

    def test_strip_whitespace_name(self):
        app = ScrapedApp(**self._valid(name="  My App  "))
        assert app.name == "My App"

    def test_strip_whitespace_bundle_id(self):
        app = ScrapedApp(**self._valid(bundle_id="  com.x  "))
        assert app.bundle_id == "com.x"

    def test_empty_name_error(self):
        with pytest.raises(ValidationError):
            ScrapedApp(**self._valid(name=""))

    def test_whitespace_only_name_error(self):
        with pytest.raises(ValidationError):
            ScrapedApp(**self._valid(name="   "))

    def test_empty_bundle_id_error(self):
        with pytest.raises(ValidationError):
            ScrapedApp(**self._valid(bundle_id=""))

    def test_name_exceeds_max_length(self):
        with pytest.raises(ValidationError):
            ScrapedApp(**self._valid(name="A" * 256))

    def test_bundle_id_exceeds_max_length(self):
        with pytest.raises(ValidationError):
            ScrapedApp(**self._valid(bundle_id="x" * 256))

    def test_icon_url_exceeds_max_length(self):
        with pytest.raises(ValidationError):
            ScrapedApp(**self._valid(icon_url="http://x.co/" + "a" * 501))

    def test_developer_name_empty_becomes_none(self):
        app = ScrapedApp(**self._valid(developer_name="   "))
        assert app.developer_name is None


# ---------------------------------------------------------------------------
# TestScrapedPriceValidation
# ---------------------------------------------------------------------------
class TestScrapedPriceValidation:
    def _valid(self, **overrides) -> dict:
        base = {
            "price": Decimal("9.99"),
            "currency": "USD",
            "region": "US",
            "timestamp": datetime(2025, 6, 1, 12, 0, 0, tzinfo=UTC),
        }
        base.update(overrides)
        return base

    def test_valid(self):
        p = ScrapedPrice(**self._valid())
        assert p.price == Decimal("9.99")

    def test_negative_price_error(self):
        with pytest.raises(ValidationError):
            ScrapedPrice(**self._valid(price=Decimal("-1")))

    def test_price_exceeds_max(self):
        with pytest.raises(ValidationError):
            ScrapedPrice(**self._valid(price=Decimal("100000000")))

    def test_price_at_max_boundary(self):
        p = ScrapedPrice(**self._valid(price=Decimal("99999999.99")))
        assert p.price == Decimal("99999999.99")

    def test_price_zero_ok(self):
        p = ScrapedPrice(**self._valid(price=Decimal("0")))
        assert p.price == Decimal("0")

    def test_currency_lowercase_normalized(self):
        p = ScrapedPrice(**self._valid(currency="eur"))
        assert p.currency == "EUR"

    def test_currency_dollar_sign(self):
        p = ScrapedPrice(**self._valid(currency="$"))
        assert p.currency == "USD"

    def test_currency_euro_sign(self):
        p = ScrapedPrice(**self._valid(currency="€"))
        assert p.currency == "EUR"

    def test_currency_invalid_error(self):
        with pytest.raises(ValidationError):
            ScrapedPrice(**self._valid(currency="INVALID"))

    def test_region_lowercase_normalized(self):
        p = ScrapedPrice(**self._valid(region="us"))
        assert p.region == "US"

    def test_region_exceeds_max_length(self):
        with pytest.raises(ValidationError):
            ScrapedPrice(**self._valid(region="TOOLONG"))

    def test_naive_timestamp_gets_utc(self):
        naive = datetime(2025, 6, 1, 12, 0, 0)
        p = ScrapedPrice(**self._valid(timestamp=naive))
        assert p.timestamp.tzinfo is UTC


# ---------------------------------------------------------------------------
# TestScrapedReviewValidation
# ---------------------------------------------------------------------------
class TestScrapedReviewValidation:
    def _valid(self, **overrides) -> dict:
        base = {
            "external_review_id": "rev-001",
            "rating": 4,
        }
        base.update(overrides)
        return base

    def test_valid_minimal(self):
        r = ScrapedReview(**self._valid())
        assert r.rating == 4

    def test_rating_zero_error(self):
        with pytest.raises(ValidationError):
            ScrapedReview(**self._valid(rating=0))

    def test_rating_six_error(self):
        with pytest.raises(ValidationError):
            ScrapedReview(**self._valid(rating=6))

    def test_rating_one_ok(self):
        r = ScrapedReview(**self._valid(rating=1))
        assert r.rating == 1

    def test_rating_five_ok(self):
        r = ScrapedReview(**self._valid(rating=5))
        assert r.rating == 5

    def test_empty_review_id_error(self):
        with pytest.raises(ValidationError):
            ScrapedReview(**self._valid(external_review_id=""))

    def test_whitespace_review_id_error(self):
        with pytest.raises(ValidationError):
            ScrapedReview(**self._valid(external_review_id="   "))

    def test_review_id_stripped(self):
        r = ScrapedReview(**self._valid(external_review_id="  rev-001  "))
        assert r.external_review_id == "rev-001"

    def test_title_exceeds_max_length(self):
        with pytest.raises(ValidationError):
            ScrapedReview(**self._valid(title="T" * 501))

    def test_author_exceeds_max_length(self):
        with pytest.raises(ValidationError):
            ScrapedReview(**self._valid(author_name="A" * 256))

    def test_strip_whitespace_title(self):
        r = ScrapedReview(**self._valid(title="  Great  "))
        assert r.title == "Great"

    def test_naive_review_date_gets_utc(self):
        naive = datetime(2025, 6, 1, 12, 0, 0)
        r = ScrapedReview(**self._valid(review_date=naive))
        assert r.review_date.tzinfo is UTC


# ---------------------------------------------------------------------------
# TestScrapeResultValidation
# ---------------------------------------------------------------------------
class TestScrapeResultValidation:
    def test_empty_url_error(self):
        with pytest.raises(ValidationError):
            ScrapeResult(url="")

    def test_whitespace_url_error(self):
        with pytest.raises(ValidationError):
            ScrapeResult(url="   ")
