from typing import Self

import httpx
import structlog
from fake_useragent import UserAgent
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.core.config import get_settings

logger = structlog.get_logger()


class RateLimitError(Exception):
    def __init__(self, retry_after: float | None = None) -> None:
        self.retry_after = retry_after
        super().__init__(f"Rate limited. Retry after: {retry_after}s")


class HTTPClient:
    def __init__(self) -> None:
        settings = get_settings()
        self._settings = settings
        self._ua = UserAgent(browsers=["Chrome", "Firefox", "Safari"])
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> Self:
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(self._settings.scraper_timeout),
            follow_redirects=True,
        )
        return self

    async def __aexit__(self, *exc: object) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    def _build_headers(self) -> dict[str, str]:
        ua = self._ua.random
        return {
            "User-Agent": ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

    async def get(self, url: str) -> httpx.Response:
        settings = self._settings
        return await self._get_with_retry(
            url,
            max_retries=settings.scraper_max_retries,
            min_wait=settings.scraper_retry_min_wait,
            max_wait=settings.scraper_retry_max_wait,
        )

    async def _get_with_retry(
        self,
        url: str,
        *,
        max_retries: int,
        min_wait: float,
        max_wait: float,
    ) -> httpx.Response:
        @retry(
            stop=stop_after_attempt(max_retries),
            wait=wait_exponential(min=min_wait, max=max_wait),
            retry=retry_if_exception_type((httpx.TimeoutException, RateLimitError)),
            reraise=True,
        )
        async def _do_request() -> httpx.Response:
            assert self._client is not None  # noqa: S101
            headers = self._build_headers()
            log = logger.bind(url=url, user_agent=headers["User-Agent"])
            log.info("http_request_start")

            response = await self._client.get(url, headers=headers)

            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                wait = float(retry_after) if retry_after else None
                log.warning("http_rate_limited", retry_after=wait)
                raise RateLimitError(retry_after=wait)

            response.raise_for_status()
            log.info("http_request_ok", status=response.status_code)
            return response

        return await _do_request()
