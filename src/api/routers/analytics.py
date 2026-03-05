"""Router for analytics endpoints backed by materialized views."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas import PaginatedResponse, PriceTrendResponse
from src.api.dependencies import PaginationParams, decode_cursor, encode_cursor
from src.core.database import get_session
from src.modules.apps.models import PriceTrend

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/price-trends", response_model=PaginatedResponse[PriceTrendResponse])
async def list_price_trends(
    app_id: uuid.UUID = Query(..., description="App UUID (required)"),
    currency: str | None = Query(None),
    region: str | None = Query(None),
    week_from: datetime | None = Query(None),
    week_to: datetime | None = Query(None),
    pagination: PaginationParams = Depends(),
    session: AsyncSession = Depends(get_session),
):
    stmt = (
        select(PriceTrend)
        .where(PriceTrend.app_id == app_id)
        .order_by(PriceTrend.week.desc())
    )

    if currency is not None:
        stmt = stmt.where(PriceTrend.currency == currency)
    if region is not None:
        stmt = stmt.where(PriceTrend.region == region)
    if week_from is not None:
        stmt = stmt.where(PriceTrend.week >= week_from)
    if week_to is not None:
        stmt = stmt.where(PriceTrend.week <= week_to)

    if pagination.cursor:
        sort_value, _ = decode_cursor(pagination.cursor)
        cursor_week = datetime.fromisoformat(sort_value)
        stmt = stmt.where(PriceTrend.week < cursor_week)

    stmt = stmt.limit(pagination.limit + 1)
    result = await session.execute(stmt)
    rows = list(result.scalars().all())

    has_more = len(rows) > pagination.limit
    items = rows[: pagination.limit]

    next_cursor = None
    if has_more and items:
        last = items[-1]
        next_cursor = encode_cursor(last.week.isoformat(), last.app_id)

    return PaginatedResponse(
        items=[PriceTrendResponse.model_validate(i) for i in items],
        next_cursor=next_cursor,
        has_more=has_more,
        count=len(items),
    )
