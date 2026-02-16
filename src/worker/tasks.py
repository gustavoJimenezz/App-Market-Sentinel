import uuid

import structlog
from sqlalchemy import select

from src.core.database import async_session_factory
from src.modules.apps.models import App, AppStore, PriceHistory, Review
from src.modules.scraping.client import HTTPClient
from src.modules.scraping.schemas import ScrapeResult
from src.modules.scraping.stores.apple import AppleStoreScraper
from src.modules.scraping.stores.google import GooglePlayScraper

logger = structlog.get_logger()


def _get_scraper(
    store: AppStore, client: HTTPClient
) -> AppleStoreScraper | GooglePlayScraper:
    if store == AppStore.APPLE_APP_STORE:
        return AppleStoreScraper(client)
    return GooglePlayScraper(client)


async def scrape_app_task(ctx: dict, app_id: str) -> dict:
    log = logger.bind(app_id=app_id)
    log.info("scrape_app_task_start")

    async with async_session_factory() as session:
        result = await session.execute(select(App).where(App.id == uuid.UUID(app_id)))
        app = result.scalar_one_or_none()

        if app is None:
            log.warning("scrape_app_not_found")
            return {"success": False, "error": "App not found"}

        async with HTTPClient() as client:
            scraper = _get_scraper(app.store, client)
            scrape_result = await scraper.scrape(app.bundle_id)

        await _save_scrape_result(session, app, scrape_result)
        log.info("scrape_app_task_done", success=scrape_result.success)
        return {"success": scrape_result.success, "error": scrape_result.error}


async def scrape_batch_task(ctx: dict, app_ids: list[str]) -> dict:
    log = logger.bind(batch_size=len(app_ids))
    log.info("scrape_batch_task_start")

    pool = ctx.get("redis")
    enqueued = 0
    for app_id in app_ids:
        if pool is not None:
            await pool.enqueue_job("scrape_app_task", app_id)
        enqueued += 1

    log.info("scrape_batch_task_done", enqueued=enqueued)
    return {"enqueued": enqueued}


async def _save_scrape_result(
    session: "AsyncSession",  # type: ignore[name-defined]  # noqa: F821
    app: App,
    result: ScrapeResult,
) -> None:
    if not result.success:
        return

    if result.app:
        app.name = result.app.name
        if result.app.developer_name:
            app.developer_name = result.app.developer_name
        if result.app.description:
            app.description = result.app.description
        if result.app.icon_url:
            app.icon_url = result.app.icon_url

    if result.price:
        price = PriceHistory(
            app_id=app.id,
            price=result.price.price,
            currency=result.price.currency,
            region=result.price.region,
            timestamp=result.price.timestamp,
        )
        session.add(price)

    for review_data in result.reviews:
        existing = await session.execute(
            select(Review).where(
                Review.app_id == app.id,
                Review.external_review_id == review_data.external_review_id,
            )
        )
        if existing.scalar_one_or_none() is None:
            review = Review(
                app_id=app.id,
                external_review_id=review_data.external_review_id,
                rating=review_data.rating,
                title=review_data.title,
                content=review_data.content,
                author_name=review_data.author_name,
                review_date=review_data.review_date,
            )
            session.add(review)

    await session.commit()
