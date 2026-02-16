"""Text processing module for review cleaning and PII anonymization."""

from src.modules.text_processing.pipeline import process_reviews_batch

__all__ = ["process_reviews_batch"]
