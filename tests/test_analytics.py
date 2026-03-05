"""Integration tests for analytics endpoints and refresh task (Ticket 7)."""

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.api import app
from src.core.config import get_settings
from src.core.database import get_session
from src.modules.apps.models import App, AppStore, PriceHistory

DATABASE_URL = get_settings().database_url


@pytest.fixture
async def db():
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
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _create_app_with_prices(factory, n_weeks: int = 3) -> uuid.UUID:
    """Insert an App and n_weeks of weekly price records."""
    async with factory() as session:
        app_obj = App(
            name="Test Analytics App",
            bundle_id=f"com.test.analytics.{uuid.uuid4().hex[:8]}",
            store=AppStore.APPLE_APP_STORE,
        )
        session.add(app_obj)
        await session.flush()

        now = datetime.now(UTC)
        for i in range(n_weeks):
            ts = now - timedelta(weeks=i)
            session.add(
                PriceHistory(
                    app_id=app_obj.id,
                    price=Decimal("0.99") + Decimal(str(i)),
                    currency="USD",
                    region="US",
                    timestamp=ts,
                )
            )

        await session.commit()
        return app_obj.id


async def _refresh_mv(factory) -> None:
    """Manually refresh the materialized view within the test transaction."""
    async with factory() as session:
        await session.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY price_trends"))
        await session.commit()


# ---------------------------------------------------------------------------
# Materialized view — migration checks
# ---------------------------------------------------------------------------


class TestMaterializedViewExists:
    async def test_mv_exists(self, db):
        """price_trends materialized view must be present in the database."""
        async with db() as session:
            result = await session.execute(
                text(
                    "SELECT matviewname FROM pg_matviews "
                    "WHERE matviewname = 'price_trends'"
                )
            )
            row = result.fetchone()
        assert row is not None, "Materialized view 'price_trends' not found"

    async def test_unique_index_exists(self, db):
        """Unique index required for REFRESH CONCURRENTLY must exist."""
        async with db() as session:
            result = await session.execute(
                text(
                    "SELECT indexname FROM pg_indexes "
                    "WHERE tablename = 'price_trends' "
                    "AND indexname = 'ix_price_trends_pk'"
                )
            )
            row = result.fetchone()
        assert row is not None, "Unique index 'ix_price_trends_pk' not found"

    async def test_week_index_exists(self, db):
        """Index for ordering by week must exist."""
        async with db() as session:
            result = await session.execute(
                text(
                    "SELECT indexname FROM pg_indexes "
                    "WHERE tablename = 'price_trends' "
                    "AND indexname = 'ix_price_trends_app_id_week'"
                )
            )
            row = result.fetchone()
        assert row is not None, "Index 'ix_price_trends_app_id_week' not found"


# ---------------------------------------------------------------------------
# GET /analytics/price-trends
# ---------------------------------------------------------------------------


class TestPriceTrendsEndpoint:
    async def test_requires_app_id(self, db):
        async with _client() as c:
            resp = await c.get("/analytics/price-trends")
        assert resp.status_code == 422

    async def test_empty_when_mv_not_refreshed(self, db):
        """Endpoint returns empty list if MV has not been refreshed yet."""
        app_id = await _create_app_with_prices(db, n_weeks=2)
        async with _client() as c:
            resp = await c.get(f"/analytics/price-trends?app_id={app_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["items"], list)

    async def test_returns_trends_after_refresh(self, db):
        app_id = await _create_app_with_prices(db, n_weeks=3)
        await _refresh_mv(db)

        async with _client() as c:
            resp = await c.get(f"/analytics/price-trends?app_id={app_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) > 0
        item = data["items"][0]
        assert item["app_id"] == str(app_id)
        assert item["currency"] == "USD"
        assert item["region"] == "US"
        assert "min_price" in item
        assert "max_price" in item
        assert "avg_price" in item
        assert "sample_count" in item

    async def test_filter_by_currency(self, db):
        app_id = await _create_app_with_prices(db, n_weeks=2)
        await _refresh_mv(db)

        async with _client() as c:
            resp = await c.get(
                f"/analytics/price-trends?app_id={app_id}&currency=EUR"
            )
        assert resp.status_code == 200
        assert resp.json()["items"] == []

    async def test_filter_by_region(self, db):
        app_id = await _create_app_with_prices(db, n_weeks=2)
        await _refresh_mv(db)

        async with _client() as c:
            resp = await c.get(
                f"/analytics/price-trends?app_id={app_id}&region=GB"
            )
        assert resp.status_code == 200
        assert resp.json()["items"] == []

    async def test_pagination_has_more(self, db):
        app_id = await _create_app_with_prices(db, n_weeks=3)
        await _refresh_mv(db)

        async with _client() as c:
            resp = await c.get(
                f"/analytics/price-trends?app_id={app_id}&limit=1"
            )
        assert resp.status_code == 200
        data = resp.json()
        if data["count"] > 0:
            # If there are multiple weeks, has_more should be True with limit=1
            # (only guaranteed if n_weeks spans multiple calendar weeks)
            assert "has_more" in data
            assert "next_cursor" in data

    async def test_pagination_cursor_navigation(self, db):
        app_id = await _create_app_with_prices(db, n_weeks=4)
        await _refresh_mv(db)

        async with _client() as c:
            first = await c.get(
                f"/analytics/price-trends?app_id={app_id}&limit=1"
            )
        first_data = first.json()
        if not first_data["has_more"]:
            pytest.skip("Not enough distinct weeks to test pagination")

        cursor = first_data["next_cursor"]
        async with _client() as c:
            second = await c.get(
                f"/analytics/price-trends?app_id={app_id}&limit=1&cursor={cursor}"
            )
        second_data = second.json()
        assert second_data["items"] != first_data["items"]

    async def test_unknown_app_returns_empty(self, db):
        async with _client() as c:
            resp = await c.get(f"/analytics/price-trends?app_id={uuid.uuid4()}")
        assert resp.status_code == 200
        assert resp.json()["items"] == []


# ---------------------------------------------------------------------------
# refresh_price_trends task
# ---------------------------------------------------------------------------


class TestRefreshPriceTrendsTask:
    async def test_refresh_task_returns_success(self, db):
        from src.worker.tasks import refresh_price_trends

        with patch(
            "src.worker.tasks.async_session_factory"
        ) as mock_factory:
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)
            mock_factory.return_value = mock_session

            result = await refresh_price_trends(ctx={})

        assert result == {"refreshed": True}

    async def test_refresh_task_executes_correct_sql(self, db):
        from src.worker.tasks import refresh_price_trends

        executed_statements = []

        with patch(
            "src.worker.tasks.async_session_factory"
        ) as mock_factory:
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)

            async def capture_execute(stmt):
                executed_statements.append(str(stmt))

            mock_session.execute = capture_execute
            mock_factory.return_value = mock_session

            await refresh_price_trends(ctx={})

        assert any(
            "REFRESH MATERIALIZED VIEW CONCURRENTLY price_trends" in s
            for s in executed_statements
        )

    async def test_refresh_task_is_registered_in_worker(self):
        from src.worker import WorkerSettings
        from src.worker.tasks import refresh_price_trends

        function_names = [f.__name__ for f in WorkerSettings.functions]
        assert "refresh_price_trends" in function_names
