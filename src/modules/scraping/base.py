import asyncio
from abc import ABC, abstractmethod

import structlog

from src.core.config import get_settings
from src.modules.scraping.client import HTTPClient
from src.modules.scraping.schemas import ScrapeResult

logger = structlog.get_logger()


class BaseScraper(ABC):
    def __init__(self, client: HTTPClient) -> None:
        self.client = client

    @abstractmethod
    def build_url(self, bundle_id: str) -> str: ...

    @abstractmethod
    async def scrape(self, bundle_id: str) -> ScrapeResult: ...

    async def scrape_batch(
        self, bundle_ids: list[str], *, concurrency: int | None = None
    ) -> list[ScrapeResult]:
        limit = concurrency or get_settings().scraper_concurrency
        semaphore = asyncio.Semaphore(limit)

        async def _limited(bid: str) -> ScrapeResult:
            async with semaphore:
                return await self._safe_scrape(bid)

        results = await asyncio.gather(
            *[_limited(bid) for bid in bundle_ids],
            return_exceptions=True,
        )

        final: list[ScrapeResult] = []
        for i, result in enumerate(results):
            if isinstance(result, BaseException):
                logger.error(
                    "scrape_batch_exception",
                    bundle_id=bundle_ids[i],
                    error=str(result),
                )
                final.append(
                    ScrapeResult(
                        url=self.build_url(bundle_ids[i]),
                        success=False,
                        error=str(result),
                    )
                )
            else:
                final.append(result)
        return final

    async def _safe_scrape(self, bundle_id: str) -> ScrapeResult:
        try:
            return await self.scrape(bundle_id)
        except Exception as exc:
            url = self.build_url(bundle_id)
            logger.error("scrape_error", url=url, error=str(exc))
            return ScrapeResult(url=url, success=False, error=str(exc))
