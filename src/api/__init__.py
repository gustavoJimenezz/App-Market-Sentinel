from fastapi import FastAPI

from src.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
