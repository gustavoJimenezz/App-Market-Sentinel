"""Integration tests for REST API endpoints (Ticket 6)."""

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.api import app
from src.core.config import get_settings
from src.core.database import get_session
from src.modules.apps.models import App, AppStore, PriceHistory, Review

DATABASE_URL = get_settings().database_url


@pytest.fixture
async def db():
    """Yield a fresh engine+session factory, dispose after test."""
    engine = create_async_engine(DATABASE_URL)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_session():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    yield factory
    app.dependency_overrides.clear()
    await engine.dispose()


def _client() -> AsyncClient:
    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    )


# ---------------------------------------------------------------------------
# Apps
# ---------------------------------------------------------------------------


class TestListApps:
    async def test_empty_list(self, db):
        async with _client() as c:
            resp = await c.get("/apps")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["items"], list)
        assert data["has_more"] is False
        assert data["next_cursor"] is None

    async def test_returns_inserted_apps(self, db):
        app_id = uuid.uuid4()
        async with db() as session:
            session.add(
                App(
                    id=app_id,
                    name="TestApp",
                    bundle_id=f"com.test.{uuid.uuid4().hex[:8]}",
                    store=AppStore.APPLE_APP_STORE,
                    is_active=True,
                )
            )
            await session.commit()

        try:
            async with _client() as c:
                resp = await c.get("/apps")
            assert resp.status_code == 200
            data = resp.json()
            assert data["count"] >= 1
            ids = [item["id"] for item in data["items"]]
            assert str(app_id) in ids
        finally:
            async with db() as session:
                obj = await session.get(App, app_id)
                if obj:
                    await session.delete(obj)
                    await session.commit()

    async def test_filter_by_store(self, db):
        app_id = uuid.uuid4()
        async with db() as session:
            session.add(
                App(
                    id=app_id,
                    name="GoogleOnlyApp",
                    bundle_id=f"com.google.{uuid.uuid4().hex[:8]}",
                    store=AppStore.GOOGLE_PLAY_STORE,
                    is_active=True,
                )
            )
            await session.commit()

        try:
            async with _client() as c:
                resp = await c.get("/apps", params={"store": "APPLE_APP_STORE"})
            data = resp.json()
            ids = [item["id"] for item in data["items"]]
            assert str(app_id) not in ids
        finally:
            async with db() as session:
                obj = await session.get(App, app_id)
                if obj:
                    await session.delete(obj)
                    await session.commit()

    async def test_filter_by_name(self, db):
        app_id = uuid.uuid4()
        unique = uuid.uuid4().hex[:8]
        async with db() as session:
            session.add(
                App(
                    id=app_id,
                    name=f"UniqueSearch{unique}",
                    bundle_id=f"com.search.{unique}",
                    store=AppStore.APPLE_APP_STORE,
                    is_active=True,
                )
            )
            await session.commit()

        try:
            async with _client() as c:
                resp = await c.get("/apps", params={"name": unique})
            data = resp.json()
            assert data["count"] >= 1
            assert any(unique in item["name"] for item in data["items"])
        finally:
            async with db() as session:
                obj = await session.get(App, app_id)
                if obj:
                    await session.delete(obj)
                    await session.commit()

    async def test_pagination_cursor(self, db):
        unique = uuid.uuid4().hex[:8]
        ids = [uuid.uuid4() for _ in range(3)]
        async with db() as session:
            for i, aid in enumerate(ids):
                session.add(
                    App(
                        id=aid,
                        name=f"Pagin{unique}_{i}",
                        bundle_id=f"com.pagin.{aid.hex[:8]}",
                        store=AppStore.APPLE_APP_STORE,
                        is_active=True,
                    )
                )
            await session.commit()

        try:
            async with _client() as c:
                resp1 = await c.get("/apps", params={"limit": 2, "name": unique})
                data1 = resp1.json()
                assert data1["count"] == 2
                assert data1["has_more"] is True
                assert data1["next_cursor"] is not None

                resp2 = await c.get(
                    "/apps",
                    params={
                        "limit": 2,
                        "cursor": data1["next_cursor"],
                        "name": unique,
                    },
                )
                data2 = resp2.json()
                assert data2["count"] >= 1

                ids_page1 = {item["id"] for item in data1["items"]}
                ids_page2 = {item["id"] for item in data2["items"]}
                assert ids_page1.isdisjoint(ids_page2)
        finally:
            async with db() as session:
                for aid in ids:
                    obj = await session.get(App, aid)
                    if obj:
                        await session.delete(obj)
                await session.commit()


class TestGetApp:
    async def test_not_found(self, db):
        async with _client() as c:
            resp = await c.get(f"/apps/{uuid.uuid4()}")
        assert resp.status_code == 404

    async def test_get_existing(self, db):
        app_id = uuid.uuid4()
        async with db() as session:
            session.add(
                App(
                    id=app_id,
                    name="DetailApp",
                    bundle_id=f"com.detail.{uuid.uuid4().hex[:8]}",
                    store=AppStore.GOOGLE_PLAY_STORE,
                    is_active=True,
                )
            )
            await session.commit()

        try:
            async with _client() as c:
                resp = await c.get(f"/apps/{app_id}")
            assert resp.status_code == 200
            data = resp.json()
            assert data["id"] == str(app_id)
            assert data["name"] == "DetailApp"
        finally:
            async with db() as session:
                obj = await session.get(App, app_id)
                if obj:
                    await session.delete(obj)
                    await session.commit()


# ---------------------------------------------------------------------------
# Prices
# ---------------------------------------------------------------------------


class TestListPriceHistory:
    async def test_requires_app_id(self, db):
        async with _client() as c:
            resp = await c.get("/prices/history")
        assert resp.status_code == 422

    async def test_empty_for_unknown_app(self, db):
        async with _client() as c:
            resp = await c.get(
                "/prices/history",
                params={"app_id": str(uuid.uuid4())},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["count"] == 0

    async def test_returns_prices(self, db):
        app_id = uuid.uuid4()
        price_id = uuid.uuid4()
        ts = datetime.now(UTC)
        async with db() as session:
            session.add(
                App(
                    id=app_id,
                    name="PriceApp",
                    bundle_id=f"com.price.{uuid.uuid4().hex[:8]}",
                    store=AppStore.APPLE_APP_STORE,
                    is_active=True,
                )
            )
            await session.flush()
            session.add(
                PriceHistory(
                    id=price_id,
                    app_id=app_id,
                    timestamp=ts,
                    price=Decimal("9.99"),
                    currency="USD",
                    region="US",
                )
            )
            await session.commit()

        try:
            async with _client() as c:
                resp = await c.get(
                    "/prices/history",
                    params={"app_id": str(app_id)},
                )
            assert resp.status_code == 200
            data = resp.json()
            assert data["count"] >= 1
            assert any(item["id"] == str(price_id) for item in data["items"])
        finally:
            async with db() as session:
                await session.execute(
                    delete(PriceHistory).where(PriceHistory.id == price_id)
                )
                obj = await session.get(App, app_id)
                if obj:
                    await session.delete(obj)
                await session.commit()

    async def test_filter_by_currency(self, db):
        app_id = uuid.uuid4()
        ts = datetime.now(UTC)
        p1 = uuid.uuid4()
        p2 = uuid.uuid4()
        async with db() as session:
            session.add(
                App(
                    id=app_id,
                    name="CurrApp",
                    bundle_id=f"com.curr.{uuid.uuid4().hex[:8]}",
                    store=AppStore.APPLE_APP_STORE,
                    is_active=True,
                )
            )
            await session.flush()
            session.add(
                PriceHistory(
                    id=p1,
                    app_id=app_id,
                    timestamp=ts,
                    price=Decimal("9.99"),
                    currency="USD",
                    region="US",
                )
            )
            session.add(
                PriceHistory(
                    id=p2,
                    app_id=app_id,
                    timestamp=ts + timedelta(seconds=1),
                    price=Decimal("8.99"),
                    currency="EUR",
                    region="DE",
                )
            )
            await session.commit()

        try:
            async with _client() as c:
                resp = await c.get(
                    "/prices/history",
                    params={"app_id": str(app_id), "currency": "EUR"},
                )
            data = resp.json()
            assert all(item["currency"] == "EUR" for item in data["items"])
        finally:
            async with db() as session:
                await session.execute(
                    delete(PriceHistory).where(PriceHistory.app_id == app_id)
                )
                obj = await session.get(App, app_id)
                if obj:
                    await session.delete(obj)
                await session.commit()


# ---------------------------------------------------------------------------
# Reviews
# ---------------------------------------------------------------------------


class TestListReviews:
    async def test_requires_app_id(self, db):
        async with _client() as c:
            resp = await c.get("/reviews")
        assert resp.status_code == 422

    async def test_empty_for_unknown_app(self, db):
        async with _client() as c:
            resp = await c.get("/reviews", params={"app_id": str(uuid.uuid4())})
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []

    async def test_returns_reviews(self, db):
        app_id = uuid.uuid4()
        review_id = uuid.uuid4()
        async with db() as session:
            session.add(
                App(
                    id=app_id,
                    name="ReviewApp",
                    bundle_id=f"com.review.{uuid.uuid4().hex[:8]}",
                    store=AppStore.APPLE_APP_STORE,
                    is_active=True,
                )
            )
            await session.flush()
            session.add(
                Review(
                    id=review_id,
                    app_id=app_id,
                    external_review_id=f"ext-{uuid.uuid4().hex[:8]}",
                    rating=5,
                    title="Great",
                    content="Love it",
                    author_name="Tester",
                    review_date=datetime.now(UTC),
                )
            )
            await session.commit()

        try:
            async with _client() as c:
                resp = await c.get("/reviews", params={"app_id": str(app_id)})
            assert resp.status_code == 200
            data = resp.json()
            assert data["count"] >= 1
            assert any(item["id"] == str(review_id) for item in data["items"])
        finally:
            async with db() as session:
                obj = await session.get(Review, review_id)
                if obj:
                    await session.delete(obj)
                app_obj = await session.get(App, app_id)
                if app_obj:
                    await session.delete(app_obj)
                await session.commit()

    async def test_filter_by_rating(self, db):
        app_id = uuid.uuid4()
        r1 = uuid.uuid4()
        r2 = uuid.uuid4()
        async with db() as session:
            session.add(
                App(
                    id=app_id,
                    name="RatingApp",
                    bundle_id=f"com.rating.{uuid.uuid4().hex[:8]}",
                    store=AppStore.APPLE_APP_STORE,
                    is_active=True,
                )
            )
            await session.flush()
            session.add(
                Review(
                    id=r1,
                    app_id=app_id,
                    external_review_id=f"ext-{uuid.uuid4().hex[:8]}",
                    rating=2,
                    title="Bad",
                    review_date=datetime.now(UTC),
                )
            )
            session.add(
                Review(
                    id=r2,
                    app_id=app_id,
                    external_review_id=f"ext-{uuid.uuid4().hex[:8]}",
                    rating=5,
                    title="Great",
                    review_date=datetime.now(UTC),
                )
            )
            await session.commit()

        try:
            async with _client() as c:
                resp = await c.get(
                    "/reviews",
                    params={"app_id": str(app_id), "rating_min": 4},
                )
            data = resp.json()
            assert all(item["rating"] >= 4 for item in data["items"])
        finally:
            async with db() as session:
                for rid in (r1, r2):
                    obj = await session.get(Review, rid)
                    if obj:
                        await session.delete(obj)
                app_obj = await session.get(App, app_id)
                if app_obj:
                    await session.delete(app_obj)
                await session.commit()

    async def test_invalid_limit(self, db):
        async with _client() as c:
            resp = await c.get(
                "/reviews",
                params={
                    "app_id": str(uuid.uuid4()),
                    "limit": 200,
                },
            )
        assert resp.status_code == 422
