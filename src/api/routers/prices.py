"""Router for price history endpoints."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import PaginationParams, decode_cursor, encode_cursor
from src.api.schemas import PaginatedResponse, PriceHistoryResponse
from src.core.database import get_session
from src.modules.apps.models import PriceHistory

router = APIRouter(prefix="/prices", tags=["prices"])


@router.get("/history", response_model=PaginatedResponse[PriceHistoryResponse])
async def list_price_history(
    app_id: uuid.UUID = Query(..., description="App UUID (required)"),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    currency: str | None = Query(None),
    region: str | None = Query(None),
    pagination: PaginationParams = Depends(),
    session: AsyncSession = Depends(get_session),
):
    stmt = (
        select(PriceHistory)
        .where(PriceHistory.app_id == app_id)
        .order_by(PriceHistory.timestamp.desc(), PriceHistory.id.desc())
    )

    if date_from is not None:
        stmt = stmt.where(PriceHistory.timestamp >= date_from)
    if date_to is not None:
        stmt = stmt.where(PriceHistory.timestamp <= date_to)
    if currency is not None:
        stmt = stmt.where(PriceHistory.currency == currency)
    if region is not None:
        stmt = stmt.where(PriceHistory.region == region)

    if pagination.cursor:
        sort_value, cursor_id = decode_cursor(pagination.cursor)
        cursor_ts = datetime.fromisoformat(sort_value)
        stmt = stmt.where(
            tuple_(PriceHistory.timestamp, PriceHistory.id)
            < tuple_(cursor_ts, cursor_id)
        )

    stmt = stmt.limit(pagination.limit + 1)
    result = await session.execute(stmt)
    rows = list(result.scalars().all())

    has_more = len(rows) > pagination.limit
    items = rows[: pagination.limit]

    next_cursor = None
    if has_more and items:
        last = items[-1]
        next_cursor = encode_cursor(last.timestamp.isoformat(), last.id)

    return PaginatedResponse(
        items=[PriceHistoryResponse.model_validate(i) for i in items],
        next_cursor=next_cursor,
        has_more=has_more,
        count=len(items),
    )
