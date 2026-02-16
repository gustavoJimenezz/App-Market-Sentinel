"""Pure normalisation functions for scraped data."""

from datetime import UTC, datetime

CURRENCY_SYMBOL_MAP: dict[str, str] = {
    "$": "USD",
    "€": "EUR",
    "£": "GBP",
    "¥": "JPY",
    "₩": "KRW",
    "₹": "INR",
    "₽": "RUB",
    "R$": "BRL",
    "₺": "TRY",
    "₫": "VND",
    "₱": "PHP",
    "฿": "THB",
    "zł": "PLN",
    "kr": "SEK",
    "Fr": "CHF",
}

VALID_CURRENCY_CODES: set[str] = {
    "AED",
    "ARS",
    "AUD",
    "BGN",
    "BRL",
    "CAD",
    "CHF",
    "CLP",
    "CNY",
    "COP",
    "CZK",
    "DKK",
    "EGP",
    "EUR",
    "GBP",
    "HKD",
    "HRK",
    "HUF",
    "IDR",
    "ILS",
    "INR",
    "JPY",
    "KRW",
    "MXN",
    "MYR",
    "NGN",
    "NOK",
    "NZD",
    "PEN",
    "PHP",
    "PKR",
    "PLN",
    "QAR",
    "RON",
    "RUB",
    "SAR",
    "SEK",
    "SGD",
    "THB",
    "TRY",
    "TWD",
    "UAH",
    "USD",
    "VND",
    "ZAR",
}


def normalize_currency(raw: str) -> str:
    """Normalize a currency symbol or code to an uppercase ISO 4217 code.

    Raises ``ValueError`` for unrecognised inputs.
    """
    stripped = raw.strip()
    if not stripped:
        raise ValueError("Currency cannot be empty")

    # Try symbol map first
    if stripped in CURRENCY_SYMBOL_MAP:
        return CURRENCY_SYMBOL_MAP[stripped]

    # Try as ISO code (case-insensitive)
    upper = stripped.upper()
    if upper in VALID_CURRENCY_CODES:
        return upper

    raise ValueError(f"Unknown currency: {raw!r}")


def ensure_timezone_aware(dt: datetime) -> datetime:
    """Return a timezone-aware datetime. Naive datetimes get UTC assigned."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt
