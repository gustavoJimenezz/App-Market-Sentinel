"""Polars-based batch pipeline for review text processing."""

from __future__ import annotations

from typing import TYPE_CHECKING

import polars as pl

from src.modules.text_processing.anonymizers import anonymize_author_name, anonymize_pii
from src.modules.text_processing.cleaners import clean_text
from src.modules.text_processing.patterns import (
    CREDIT_CARD_MASK,
    CREDIT_CARD_PATTERN,
    EMAIL_MASK,
    EMAIL_PATTERN,
    HTML_TAG_PATTERN,
    SSN_MASK,
    SSN_PATTERN,
    URL_PATTERN,
)

if TYPE_CHECKING:
    from src.modules.scraping.schemas import ScrapedReview


def process_reviews_batch(reviews: list[ScrapedReview]) -> list[dict]:
    """Process a batch of reviews using Polars for vectorized text operations.

    Returns a list of dicts with keys:
        - external_review_id
        - title_processed
        - content_processed
        - author_name_processed
        - processing_metadata
    """
    if not reviews:
        return []

    df = pl.DataFrame(
        {
            "external_review_id": [r.external_review_id for r in reviews],
            "title": [r.title for r in reviews],
            "content": [r.content for r in reviews],
            "author_name": [r.author_name for r in reviews],
        },
        schema={
            "external_review_id": pl.Utf8,
            "title": pl.Utf8,
            "content": pl.Utf8,
            "author_name": pl.Utf8,
        },
    )

    # --- Cleaning: vectorized Polars str operations (Rust-native) ---
    df = df.with_columns(
        _clean_column("title").alias("title_clean"),
        _clean_column("content").alias("content_clean"),
    )

    # --- PII detection flags (before anonymization, on original content) ---
    df = df.with_columns(
        pl.col("content").fill_null("").str.contains(EMAIL_PATTERN).alias("had_email"),
        pl.col("content")
        .fill_null("")
        .str.contains(CREDIT_CARD_PATTERN)
        .alias("had_credit_card"),
        pl.col("content").fill_null("").str.contains(SSN_PATTERN).alias("had_ssn"),
    )

    # --- Anonymization: vectorized where possible, map_elements for complex ---
    df = df.with_columns(
        _anonymize_column("title_clean").alias("title_processed"),
        _anonymize_column("content_clean").alias("content_processed"),
        pl.col("author_name")
        .map_elements(
            lambda x: anonymize_author_name(x) if x is not None else None,
            return_dtype=pl.Utf8,
        )
        .alias("author_name_processed"),
    )

    # --- Build processing metadata ---
    df = df.with_columns(
        pl.struct(
            pl.col("content").fill_null("").str.len_chars().alias("original_length"),
            pl.col("content_processed")
            .fill_null("")
            .str.len_chars()
            .alias("processed_length"),
            pl.col("had_email"),
            pl.col("had_credit_card"),
            pl.col("had_ssn"),
        ).alias("processing_metadata")
    )

    result = df.select(
        "external_review_id",
        "title_processed",
        "content_processed",
        "author_name_processed",
        "processing_metadata",
    ).to_dicts()

    # Convert struct metadata to plain dict
    for row in result:
        meta = row["processing_metadata"]
        if isinstance(meta, dict):
            row["processing_metadata"] = {
                "original_length": meta["original_length"],
                "processed_length": meta["processed_length"],
                "had_email": meta["had_email"],
                "had_credit_card": meta["had_credit_card"],
                "had_ssn": meta["had_ssn"],
            }

    return result


def _clean_column(col_name: str) -> pl.Expr:
    """Build a Polars expression that cleans a text column using vectorized ops."""
    return (
        pl.when(pl.col(col_name).is_not_null())
        .then(
            pl.col(col_name)
            .str.replace_all(HTML_TAG_PATTERN, "")
            .str.replace_all(URL_PATTERN, "")
            .str.to_lowercase()
            .str.replace_all(r"\s+", " ")
            .str.strip_chars()
        )
        .otherwise(pl.lit(None, dtype=pl.Utf8))
    )


def _anonymize_column(col_name: str) -> pl.Expr:
    """Build a Polars expression that anonymizes PII using vectorized regex."""
    return (
        pl.when(pl.col(col_name).is_not_null())
        .then(
            pl.col(col_name)
            .str.replace_all(EMAIL_PATTERN, EMAIL_MASK)
            .str.replace_all(CREDIT_CARD_PATTERN, CREDIT_CARD_MASK)
            .str.replace_all(SSN_PATTERN, SSN_MASK)
        )
        .otherwise(pl.lit(None, dtype=pl.Utf8))
    )
