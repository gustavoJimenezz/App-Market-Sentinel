# Ticket 1: Setup de Infraestructura Asincrona & Docker

**Fecha:** 2026-02-09

## Resumen

Configuracion del entorno de desarrollo reproducible para Market Sentinel usando Docker Compose. Se establecieron los fundamentos del proyecto: gestion de dependencias con Poetry, configuracion centralizada con Pydantic Settings, linting con Ruff y hooks de pre-commit.

## Cambios Principales

- Creacion del proyecto Python con Poetry (`pyproject.toml`) y todas las dependencias async (FastAPI, SQLAlchemy 2.0, asyncpg, httpx, arq, Polars, structlog)
- Orquestacion Docker Compose con 3 servicios: PostgreSQL 16, Redis 7 y la aplicacion
- Dockerfile basado en `python:3.12-slim` con Poetry para gestion de dependencias
- Configuracion centralizada via `Pydantic Settings` con carga automatica de `.env`
- App FastAPI minima con endpoint `/health` para verificacion de despliegue
- Linter Ruff configurado con reglas estrictas (pycodestyle, pyflakes, isort, naming, bugbear, simplify)
- Pre-commit hooks para calidad de codigo automatica

## Flujo de Trabajo

1. El desarrollador ejecuta `docker-compose up --build`
2. Docker Compose levanta PostgreSQL y Redis con healthchecks
3. Una vez saludables, se construye y levanta el servicio `app`
4. Uvicorn arranca FastAPI en el puerto 8000 con hot-reload
5. Pydantic Settings carga la configuracion desde `.env`
6. El endpoint `/health` responde `{"status": "ok"}` confirmando que todo funciona

```
[docker-compose up] -> [Postgres 16 + Redis 7 healthcheck]
                    -> [Build Dockerfile (Poetry install)]
                    -> [Uvicorn :8000] -> [GET /health -> {"status": "ok"}]
```

## Archivos Afectados

| Archivo | Cambio |
|---------|--------|
| `.gitignore` | Exclusiones para Python, venvs, IDE, Docker, Ruff, pytest |
| `pyproject.toml` | Proyecto Poetry con dependencias principales y dev, config Ruff y pytest |
| `poetry.lock` | Lock de dependencias generado |
| `src/__init__.py` | Paquete raiz |
| `src/api/__init__.py` | App FastAPI con endpoint `/health` |
| `src/core/__init__.py` | Paquete core |
| `src/core/config.py` | Clase `Settings` con Pydantic Settings y factory `get_settings()` |
| `src/modules/__init__.py` | Paquete modules (placeholder para logica de negocio) |
| `src/worker/__init__.py` | Paquete worker (placeholder para tareas async con arq) |
| `.env.example` | Variables de entorno documentadas con valores de ejemplo |
| `Dockerfile` | Imagen Python 3.12-slim con Poetry 1.8.5, CMD uvicorn |
| `docker-compose.yml` | Servicios: postgres, redis, app con healthchecks y volumes |
| `.pre-commit-config.yaml` | Hooks: trailing-whitespace, end-of-file, check-yaml, ruff lint+format |

## Notas Tecnicas

- **Layout src/:** Se usa el patron `src/` layout para separar el codigo fuente del directorio raiz, evitando imports accidentales
- **Pydantic Settings:** Configuracion tipada y validada automaticamente. Se usa `@lru_cache` en `get_settings()` para instancia singleton
- **Dockerfile sin multi-stage:** Intencionalmente simple; el hardening de la imagen se realizara en el Ticket 9
- **Hot-reload:** Uvicorn corre con `--reload` y el codigo se monta como volumen (`.:/app`) para desarrollo agil
- **Healthchecks:** Postgres usa `pg_isready`, Redis usa `redis-cli ping`. El servicio app solo arranca cuando ambos estan saludables (`condition: service_healthy`)
- **Variables de entorno necesarias:** `DATABASE_URL`, `REDIS_URL`, `APP_NAME`, `DEBUG`, `LOG_LEVEL`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`
- **DoD pendiente:** Ejecutar `docker-compose up --build` y verificar que `curl localhost:8000/health` retorna `{"status": "ok"}`
