from arq.connections import ArqRedis, RedisSettings, create_pool
from fastapi import FastAPI, HTTPException

from src.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
)

_arq_pool: ArqRedis | None = None


def _redis_settings() -> RedisSettings:
    url = settings.redis_url
    parts = url.replace("redis://", "").split("/")
    host_port = parts[0]
    database = int(parts[1]) if len(parts) > 1 else 0
    host, _, port = host_port.partition(":")
    return RedisSettings(
        host=host or "localhost",
        port=int(port) if port else 6379,
        database=database,
    )


async def _get_arq_pool() -> ArqRedis:
    global _arq_pool  # noqa: PLW0603
    if _arq_pool is None:
        _arq_pool = await create_pool(_redis_settings())
    return _arq_pool


@app.on_event("shutdown")
async def _close_arq_pool() -> None:
    global _arq_pool  # noqa: PLW0603
    if _arq_pool is not None:
        await _arq_pool.aclose()
        _arq_pool = None


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/scrape/{app_id}")
async def scrape_app(app_id: str) -> dict[str, str]:
    pool = await _get_arq_pool()
    job = await pool.enqueue_job("scrape_app_task", app_id)
    if job is None:
        raise HTTPException(status_code=409, detail="Job already enqueued")
    return {"job_id": job.job_id}
