"""Router for app listing and detail endpoints."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import PaginationParams, decode_cursor, encode_cursor
from src.api.schemas import AppResponse, PaginatedResponse
from src.core.database import get_session
from src.modules.apps.models import App, AppStore

router = APIRouter(prefix="/apps", tags=["apps"])


@router.get("", response_model=PaginatedResponse[AppResponse])
async def list_apps(
    pagination: PaginationParams = Depends(),
    store: AppStore | None = Query(None),
    is_active: bool | None = Query(None),
    name: str | None = Query(None, description="Search by name (case-insensitive)"),
    session: AsyncSession = Depends(get_session),
):
    stmt = select(App).order_by(App.created_at.desc(), App.id.desc())

    if store is not None:
        stmt = stmt.where(App.store == store)
    if is_active is not None:
        stmt = stmt.where(App.is_active == is_active)
    if name is not None:
        stmt = stmt.where(App.name.ilike(f"%{name}%"))

    if pagination.cursor:
        sort_value, cursor_id = decode_cursor(pagination.cursor)
        cursor_ts = datetime.fromisoformat(sort_value)
        stmt = stmt.where(tuple_(App.created_at, App.id) < tuple_(cursor_ts, cursor_id))

    stmt = stmt.limit(pagination.limit + 1)
    result = await session.execute(stmt)
    rows = list(result.scalars().all())

    has_more = len(rows) > pagination.limit
    items = rows[: pagination.limit]

    next_cursor = None
    if has_more and items:
        last = items[-1]
        next_cursor = encode_cursor(last.created_at.isoformat(), last.id)

    return PaginatedResponse(
        items=[AppResponse.model_validate(i) for i in items],
        next_cursor=next_cursor,
        has_more=has_more,
        count=len(items),
    )


@router.get("/{app_id}", response_model=AppResponse)
async def get_app(
    app_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    app = await session.get(App, app_id)
    if app is None:
        raise HTTPException(status_code=404, detail="App not found")
    return AppResponse.model_validate(app)
