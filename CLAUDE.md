# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Comunicación

- Toda la comunicación con el usuario debe ser en **español**.

## Contexto del Proyecto

El contexto general del proyecto se encuentra en `README.md` y en los archivos dentro de `programa-AI-AppSec/` (visión, fases y tickets del roadmap).

## Project Overview

**Market Sentinel** — An async-first SaaS & App Store analytics platform for competitive intelligence. Ingests, normalizes, and analyzes data (pricing, reviews, changelogs) from app marketplaces. Currently in Phase 1 (MVP): Foundation & Core Infrastructure.

## Tech Stack

- **Python 3.12+** (async-first, fully typed)
- **FastAPI** + Uvicorn (async REST API)
- **PostgreSQL 16** via async SQLAlchemy 2.0 + asyncpg
- **Redis 7** + Arq (async background task queue)
- **Polars** (data processing, replaces Pandas)
- **Pydantic Settings** (typed config from `.env`)
- **structlog** (JSON structured logging)
- **Docker Compose** (postgres, redis, app services)
- **Poetry** (dependency management)

## Common Commands

```bash
# Start all services (postgres, redis, app on :8000)
docker-compose up --build

# Run locally (requires postgres/redis running separately)
poetry run uvicorn src.api:app --reload --host 0.0.0.0 --port 8000

# Lint and format
ruff check src/ --fix
ruff format src/

# Run tests
poetry run pytest

# Run a single test file
poetry run pytest tests/test_example.py

# Pre-commit hooks (install once, then runs on every commit)
pre-commit install
pre-commit run --all-files

# Database migrations (when Alembic is configured)
poetry run alembic upgrade head
```

## Architecture

**Modular monolith** with producer-consumer pattern:

```
src/
├── api/          # FastAPI app, REST endpoints (read/query operations)
│   └── __init__.py   # App instance, health endpoint at /health
├── core/         # Shared config and utilities
│   └── config.py     # Pydantic Settings (singleton via @lru_cache)
├── modules/      # Business logic domains (apps, scraping, analytics)
└── worker/       # Arq background jobs (scraping, data processing)
```

- **API layer** handles HTTP requests, produces jobs to Redis queue
- **Worker layer** consumes jobs for intensive operations (scraping, processing)
- **Redis** decouples API from workers as message broker
- All I/O is async — database queries, HTTP requests, task handling

## Configuration

Settings loaded from `.env` via Pydantic Settings (`src/core/config.py`). Use `get_settings()` which returns a cached singleton. See `.env.example` for all variables:

| Variable | Default | Purpose |
|----------|---------|---------|
| `DATABASE_URL` | `postgresql+asyncpg://sentinel:sentinel@postgres:5432/sentinel` | Async PG connection |
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection |
| `DEBUG` | `false` | Debug mode |
| `LOG_LEVEL` | `INFO` | Logging level |

## Ruff Configuration

Target: Python 3.12, line length: 88. Enabled rule sets: `E`, `W`, `F`, `I`, `N`, `UP`, `B`, `SIM`, `TCH`. First-party imports: `src`. Pre-commit hooks run ruff check + format automatically.

## Docker Services

- **postgres**: PostgreSQL 16 Alpine on port 5432 (with healthcheck)
- **redis**: Redis 7 Alpine on port 6379 (with healthcheck)
- **app**: FastAPI on port 8000, waits for healthy postgres + redis. Source mounted at `/app` for hot reload.

## Testing

pytest with `asyncio_mode = "auto"` — async test functions work without decorators. Test directory: `tests/`.
