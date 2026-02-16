import structlog
from arq import cron  # noqa: F401
from arq.connections import RedisSettings

from src.core.config import get_settings
from src.worker.tasks import scrape_app_task, scrape_batch_task

logger = structlog.get_logger()


async def startup(ctx: dict) -> None:
    logger.info("worker_startup")


async def shutdown(ctx: dict) -> None:
    logger.info("worker_shutdown")


def _redis_settings() -> RedisSettings:
    settings = get_settings()
    url = settings.redis_url
    # Parse redis://host:port/db
    parts = url.replace("redis://", "").split("/")
    host_port = parts[0]
    database = int(parts[1]) if len(parts) > 1 else 0
    host, _, port = host_port.partition(":")
    return RedisSettings(
        host=host or "localhost",
        port=int(port) if port else 6379,
        database=database,
    )


class WorkerSettings:
    functions = [scrape_app_task, scrape_batch_task]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = _redis_settings()
    max_jobs = 10
    job_timeout = 300
