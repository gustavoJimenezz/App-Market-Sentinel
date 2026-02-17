"""Cursor-based pagination utilities."""

import base64
import uuid
from dataclasses import dataclass

from fastapi import Query


@dataclass
class PaginationParams:
    cursor: str | None = Query(
        None, description="Pagination cursor from previous response"
    )
    limit: int = Query(50, ge=1, le=100, description="Number of items per page")


def encode_cursor(sort_value: str, row_id: uuid.UUID) -> str:
    """Encode a (sort_value, id) pair into a base64 cursor string."""
    raw = f"{sort_value}:{row_id}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def decode_cursor(cursor: str) -> tuple[str, uuid.UUID]:
    """Decode a base64 cursor string into (sort_value, UUID)."""
    raw = base64.urlsafe_b64decode(cursor.encode()).decode()
    sort_value, id_str = raw.rsplit(":", 1)
    return sort_value, uuid.UUID(id_str)
