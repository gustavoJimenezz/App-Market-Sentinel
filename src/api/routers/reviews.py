"""Router for review endpoints."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import PaginationParams, decode_cursor, encode_cursor
from src.api.schemas import PaginatedResponse, ReviewResponse
from src.core.database import get_session
from src.modules.apps.models import Review

router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.get("", response_model=PaginatedResponse[ReviewResponse])
async def list_reviews(
    app_id: uuid.UUID = Query(..., description="App UUID (required)"),
    rating_min: int | None = Query(None, ge=1, le=5),
    rating_max: int | None = Query(None, ge=1, le=5),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    pagination: PaginationParams = Depends(),
    session: AsyncSession = Depends(get_session),
):
    stmt = (
        select(Review)
        .where(Review.app_id == app_id)
        .order_by(Review.review_date.desc().nullslast(), Review.id.desc())
    )

    if rating_min is not None:
        stmt = stmt.where(Review.rating >= rating_min)
    if rating_max is not None:
        stmt = stmt.where(Review.rating <= rating_max)
    if date_from is not None:
        stmt = stmt.where(Review.review_date >= date_from)
    if date_to is not None:
        stmt = stmt.where(Review.review_date <= date_to)

    if pagination.cursor:
        sort_value, cursor_id = decode_cursor(pagination.cursor)
        cursor_ts = datetime.fromisoformat(sort_value) if sort_value else None
        stmt = stmt.where(
            tuple_(Review.review_date, Review.id) < tuple_(cursor_ts, cursor_id)
        )

    stmt = stmt.limit(pagination.limit + 1)
    result = await session.execute(stmt)
    rows = list(result.scalars().all())

    has_more = len(rows) > pagination.limit
    items = rows[: pagination.limit]

    next_cursor = None
    if has_more and items:
        last = items[-1]
        review_date_str = last.review_date.isoformat() if last.review_date else ""
        next_cursor = encode_cursor(review_date_str, last.id)

    return PaginatedResponse(
        items=[ReviewResponse.model_validate(i) for i in items],
        next_cursor=next_cursor,
        has_more=has_more,
        count=len(items),
    )
