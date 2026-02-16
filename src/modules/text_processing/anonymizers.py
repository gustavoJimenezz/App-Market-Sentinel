"""Pure functions for PII anonymization."""

from src.modules.text_processing.patterns import (
    CREDIT_CARD_MASK,
    CREDIT_CARD_RE,
    EMAIL_MASK,
    EMAIL_RE,
    PHONE_MASK,
    PHONE_RE,
    SSN_MASK,
    SSN_RE,
)


def anonymize_emails(text: str) -> str:
    """Replace email addresses with [EMAIL]."""
    return EMAIL_RE.sub(EMAIL_MASK, text)


def anonymize_phones(text: str) -> str:
    """Replace phone numbers with [PHONE]."""
    return PHONE_RE.sub(PHONE_MASK, text)


def anonymize_credit_cards(text: str) -> str:
    """Replace credit card numbers with [CREDIT_CARD]."""
    return CREDIT_CARD_RE.sub(CREDIT_CARD_MASK, text)


def anonymize_ssn(text: str) -> str:
    """Replace SSN-like patterns with [SSN]."""
    return SSN_RE.sub(SSN_MASK, text)


def anonymize_author_name(name: str) -> str:
    """Convert full name to initials: 'John Doe' -> 'J. D.'"""
    stripped = name.strip()
    if not stripped:
        return ""
    parts = stripped.split()
    return " ".join(f"{p[0].upper()}." for p in parts)


def anonymize_pii(text: str) -> str:
    """Apply all PII anonymization rules (except author name)."""
    text = anonymize_emails(text)
    text = anonymize_credit_cards(text)
    text = anonymize_ssn(text)
    text = anonymize_phones(text)
    return text
