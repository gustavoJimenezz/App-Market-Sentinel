"""Tests for the Polars-based text processing pipeline."""

import time

from src.modules.scraping.schemas import ScrapedReview
from src.modules.text_processing.pipeline import process_reviews_batch


def _make_review(**overrides) -> ScrapedReview:
    base = {
        "external_review_id": "rev-001",
        "rating": 5,
        "title": "Great App",
        "content": "This app is wonderful.",
        "author_name": "John Doe",
    }
    return ScrapedReview(**(base | overrides))


class TestProcessReviewsBatch:
    def test_empty_list(self):
        assert process_reviews_batch([]) == []

    def test_single_review(self):
        result = process_reviews_batch([_make_review()])
        assert len(result) == 1
        assert result[0]["external_review_id"] == "rev-001"

    def test_preserves_external_id(self):
        reviews = [
            _make_review(external_review_id="a"),
            _make_review(external_review_id="b"),
        ]
        result = process_reviews_batch(reviews)
        ids = {r["external_review_id"] for r in result}
        assert ids == {"a", "b"}

    def test_html_removed_from_content(self):
        review = _make_review(content="<b>bold</b> text")
        result = process_reviews_batch([review])
        assert "<b>" not in result[0]["content_processed"]
        assert "bold text" in result[0]["content_processed"]

    def test_html_removed_from_title(self):
        review = _make_review(title="<i>Fancy</i> Title")
        result = process_reviews_batch([review])
        assert "<i>" not in result[0]["title_processed"]

    def test_lowercased(self):
        review = _make_review(content="THIS IS LOUD")
        result = process_reviews_batch([review])
        assert result[0]["content_processed"] == "this is loud"

    def test_urls_removed(self):
        review = _make_review(content="visit https://spam.com now")
        result = process_reviews_batch([review])
        assert "https://spam.com" not in result[0]["content_processed"]

    def test_email_anonymized(self):
        review = _make_review(content="contact me at user@example.com")
        result = process_reviews_batch([review])
        assert "[EMAIL]" in result[0]["content_processed"]
        assert "user@example.com" not in result[0]["content_processed"]

    def test_credit_card_anonymized(self):
        review = _make_review(content="card 4111 1111 1111 1111")
        result = process_reviews_batch([review])
        assert "[CREDIT_CARD]" in result[0]["content_processed"]

    def test_ssn_anonymized(self):
        review = _make_review(content="ssn 123-45-6789")
        result = process_reviews_batch([review])
        assert "[SSN]" in result[0]["content_processed"]

    def test_author_name_anonymized(self):
        review = _make_review(author_name="John Doe")
        result = process_reviews_batch([review])
        assert result[0]["author_name_processed"] == "J. D."

    def test_none_fields_handled(self):
        review = _make_review(title=None, content=None, author_name=None)
        result = process_reviews_batch([review])
        assert result[0]["title_processed"] is None
        assert result[0]["content_processed"] is None
        assert result[0]["author_name_processed"] is None

    def test_metadata_generated(self):
        review = _make_review(content="email: test@mail.com")
        result = process_reviews_batch([review])
        meta = result[0]["processing_metadata"]
        assert "original_length" in meta
        assert "processed_length" in meta
        assert meta["had_email"] is True

    def test_metadata_no_pii(self):
        review = _make_review(content="clean review text")
        result = process_reviews_batch([review])
        meta = result[0]["processing_metadata"]
        assert meta["had_email"] is False
        assert meta["had_credit_card"] is False
        assert meta["had_ssn"] is False


class TestPerformance:
    def test_10k_reviews_under_1_second(self):
        """Definition of Done: 10k reviews processed in < 1 second."""
        reviews = [
            _make_review(
                external_review_id=f"rev-{i}",
                content=(
                    f"This is review number {i}. "
                    "The app is great but could be better. "
                    "Contact support@example.com for help. "
                    "Visit https://example.com/faq for more info. "
                    "<b>Highly recommended!</b> "
                ) * 3,
                title=f"Review Title {i}",
                author_name=f"User Name {i}",
            )
            for i in range(10_000)
        ]

        start = time.perf_counter()
        result = process_reviews_batch(reviews)
        elapsed = time.perf_counter() - start

        assert len(result) == 10_000
        assert elapsed < 1.0, f"Processing took {elapsed:.2f}s, expected < 1.0s"
