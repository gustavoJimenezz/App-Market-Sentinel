"""Tests for database schema: apps, price_history (partitioned), reviews (JSONB)."""

import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.core.config import get_settings
from src.modules.apps.models import App, AppStore

DATABASE_URL = get_settings().database_url


async def _make_session():
    engine = create_async_engine(DATABASE_URL)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return engine, factory


async def test_insert_app():
    """Inserting an App row should persist and return the expected fields."""
    engine, factory = await _make_session()
    async with factory() as session:
        app = App(
            id=uuid.uuid4(),
            name="Test App",
            bundle_id=f"com.test.{uuid.uuid4().hex[:8]}",
            store=AppStore.APPLE_APP_STORE,
            developer_name="Test Dev",
            is_active=True,
        )
        session.add(app)
        await session.flush()

        result = await session.get(App, app.id)
        assert result is not None
        assert result.name == "Test App"
        assert result.store == AppStore.APPLE_APP_STORE
        assert result.bundle_id == app.bundle_id

        await session.rollback()
    await engine.dispose()


async def test_partitions_exist():
    """price_history should have at least 24 child partitions."""
    engine, factory = await _make_session()
    async with factory() as session:
        result = await session.execute(
            text("""
                SELECT count(*)
                FROM pg_inherits
                JOIN pg_class parent ON pg_inherits.inhparent = parent.oid
                JOIN pg_class child  ON pg_inherits.inhrelid  = child.oid
                WHERE parent.relname = 'price_history';
            """)
        )
        count = result.scalar_one()
        assert count >= 24, f"Expected >=24 partitions, got {count}"
    await engine.dispose()


async def test_gin_index_exists():
    """reviews table should have a GIN index on the metadata column."""
    engine, factory = await _make_session()
    async with factory() as session:
        result = await session.execute(
            text("""
                SELECT indexname
                FROM pg_indexes
                WHERE tablename = 'reviews'
                  AND indexdef ILIKE '%gin%';
            """)
        )
        rows = result.fetchall()
        gin_names = [r[0] for r in rows]
        assert any("metadata" in name for name in gin_names), (
            f"No GIN index on metadata found. Indexes: {gin_names}"
        )
    await engine.dispose()


async def test_brin_index_exists():
    """price_history should have a BRIN index on timestamp."""
    engine, factory = await _make_session()
    async with factory() as session:
        result = await session.execute(
            text("""
                SELECT indexname
                FROM pg_indexes
                WHERE tablename = 'price_history'
                  AND indexdef ILIKE '%brin%';
            """)
        )
        rows = result.fetchall()
        assert len(rows) >= 1, "No BRIN index found on price_history"
    await engine.dispose()


async def test_enum_type_exists():
    """The app_store_enum PostgreSQL type should exist."""
    engine, factory = await _make_session()
    async with factory() as session:
        result = await session.execute(
            text("""
                SELECT typname
                FROM pg_type
                WHERE typname = 'app_store_enum';
            """)
        )
        row = result.fetchone()
        assert row is not None, "app_store_enum type not found in pg_type"
    await engine.dispose()
