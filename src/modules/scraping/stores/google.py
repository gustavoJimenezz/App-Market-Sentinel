from src.modules.scraping.base import BaseScraper
from src.modules.scraping.client import HTTPClient
from src.modules.scraping.schemas import ScrapeResult


class GooglePlayScraper(BaseScraper):
    BASE_URL = "https://play.google.com/store/apps/details"

    def __init__(self, client: HTTPClient) -> None:
        super().__init__(client)

    def build_url(self, bundle_id: str) -> str:
        return f"{self.BASE_URL}?id={bundle_id}&hl=en&gl=US"

    async def scrape(self, bundle_id: str) -> ScrapeResult:
        raise NotImplementedError("Google Play scraper not yet implemented")
