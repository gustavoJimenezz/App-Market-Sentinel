"""Pydantic response models for the REST API."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

from src.modules.apps.models import AppStore

T = TypeVar("T")


class AppResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    bundle_id: str
    store: AppStore
    developer_name: str | None
    description: str | None
    icon_url: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class PriceHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    app_id: uuid.UUID
    timestamp: datetime
    price: Decimal
    currency: str
    region: str


class ReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    app_id: uuid.UUID
    external_review_id: str
    rating: int
    title: str | None
    content: str | None
    author_name: str | None
    review_date: datetime | None
    metadata_: dict | None
    created_at: datetime
    updated_at: datetime


class PriceTrendResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    app_id: uuid.UUID
    currency: str
    region: str
    week: datetime
    min_price: Decimal
    max_price: Decimal
    avg_price: Decimal
    sample_count: int


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    next_cursor: str | None
    has_more: bool
    count: int
