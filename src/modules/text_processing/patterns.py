"""Compiled regex patterns for text cleaning and PII detection."""

import re

# --- Text cleaning patterns ---
HTML_TAG_RE = re.compile(r"<[^>]+>")
URL_RE = re.compile(
    r"https?://[^\s<>\"']+|www\.[^\s<>\"']+",
    re.IGNORECASE,
)
EMOJI_RE = re.compile(
    "["
    "\U0001f600-\U0001f64f"  # emoticons
    "\U0001f300-\U0001f5ff"  # symbols & pictographs
    "\U0001f680-\U0001f6ff"  # transport & map
    "\U0001f1e0-\U0001f1ff"  # flags
    "\U00002702-\U000027b0"  # dingbats
    "\U0000fe00-\U0000fe0f"  # variation selectors
    "\U0001f900-\U0001f9ff"  # supplemental symbols
    "\U0001fa00-\U0001fa6f"  # chess symbols
    "\U0001fa70-\U0001faff"  # symbols extended-A
    "\U00002600-\U000026ff"  # misc symbols
    "\U00002b50-\U00002b55"  # stars and circles
    "]+",
)
MULTI_WHITESPACE_RE = re.compile(r"\s+")

# --- PII patterns ---
EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_RE = re.compile(
    r"(?:\+?\d{1,3}[-.\s]?)?"  # country code
    r"(?:\(?\d{2,4}\)?[-.\s]?)"  # area code
    r"(?:\d{3,4}[-.\s]?)"  # first group
    r"\d{3,4}"  # last group
)
CREDIT_CARD_RE = re.compile(
    r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b"
)
SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")

# --- Replacement masks ---
EMAIL_MASK = "[EMAIL]"
PHONE_MASK = "[PHONE]"
CREDIT_CARD_MASK = "[CREDIT_CARD]"
SSN_MASK = "[SSN]"

# --- Polars-compatible pattern strings (for .str.replace_all) ---
HTML_TAG_PATTERN = r"<[^>]+>"
URL_PATTERN = r"https?://[^\s<>\"']+|www\.[^\s<>\"']+"
EMAIL_PATTERN = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
CREDIT_CARD_PATTERN = r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b"
SSN_PATTERN = r"\b\d{3}-\d{2}-\d{4}\b"
