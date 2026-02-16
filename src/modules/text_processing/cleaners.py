"""Pure functions for text cleaning."""

from src.modules.text_processing.patterns import (
    EMOJI_RE,
    HTML_TAG_RE,
    MULTI_WHITESPACE_RE,
    URL_RE,
)


def remove_html_tags(text: str) -> str:
    """Remove HTML tags from text."""
    return HTML_TAG_RE.sub("", text)


def remove_urls(text: str) -> str:
    """Remove HTTP/HTTPS/www URLs from text."""
    return URL_RE.sub("", text)


def normalize_whitespace(text: str) -> str:
    """Collapse multiple whitespace characters into a single space and strip."""
    return MULTI_WHITESPACE_RE.sub(" ", text).strip()


def remove_emojis(text: str) -> str:
    """Remove emoji characters from text."""
    return EMOJI_RE.sub("", text)


def clean_text(text: str) -> str:
    """Apply full cleaning pipeline: HTML, URLs, emojis, lowercase, whitespace."""
    text = remove_html_tags(text)
    text = remove_urls(text)
    text = remove_emojis(text)
    text = text.lower()
    text = normalize_whitespace(text)
    return text
