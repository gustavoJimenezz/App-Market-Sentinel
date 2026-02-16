import uuid
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from src.modules.apps.models import App
from src.modules.scraping.schemas import (
    ScrapedApp,
    ScrapedPrice,
    ScrapedReview,
    ScrapeResult,
)
from src.worker.tasks import _save_scrape_result, scrape_app_task


async def test_save_scrape_result_creates_price():
    """_save_scrape_result should add PriceHistory to session."""
    app_id = uuid.uuid4()
    app = MagicMock(spec=App)
    app.id = app_id

    session = AsyncMock()
    # Mock the review dedup query to return no existing review
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    session.execute = AsyncMock(return_value=mock_result)

    result = ScrapeResult(
        url="http://test",
        app=ScrapedApp(
            name="Updated App",
            bundle_id="com.test",
            developer_name="Dev",
        ),
        price=ScrapedPrice(
            price=Decimal("9.99"),
            currency="USD",
            region="US",
            timestamp=datetime.now(UTC),
        ),
        reviews=[
            ScrapedReview(
                external_review_id="ext-1",
                rating=5,
                title="Great",
                content="Love it",
                author_name="Tester",
            ),
        ],
        success=True,
    )

    await _save_scrape_result(session, app, result)

    # Verify app metadata was updated
    assert app.name == "Updated App"
    assert app.developer_name == "Dev"

    # Verify session.add was called (price + review)
    assert session.add.call_count == 2
    assert session.commit.called


async def test_save_scrape_result_skips_on_failure():
    """_save_scrape_result should do nothing if result is not successful."""
    session = AsyncMock()
    app = MagicMock(spec=App)

    result = ScrapeResult(url="http://test", success=False, error="fail")
    await _save_scrape_result(session, app, result)

    session.add.assert_not_called()
    session.commit.assert_not_called()


async def test_scrape_app_task_app_not_found():
    """scrape_app_task should return error when app doesn't exist."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    with patch("src.worker.tasks.async_session_factory", return_value=mock_session):
        result = await scrape_app_task({}, str(uuid.uuid4()))

    assert result["success"] is False
    assert "not found" in result["error"].lower()
