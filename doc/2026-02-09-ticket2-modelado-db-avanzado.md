# Ticket 2 — Modelado de DB Avanzado

**Fecha:** 2026-02-09

## Resumen

Implementación del esquema de base de datos con modelos SQLAlchemy async, migraciones Alembic y tabla particionada `price_history`. Se creó la infraestructura de conexión async a PostgreSQL, los modelos de dominio (App, PriceHistory, Review) y una migración manual con particionamiento por rango, índices BRIN/GIN y tests de verificación del esquema.

## Cambios Principales

- Creada infraestructura DB async: engine con pool, session factory, `Base` declarativa con naming convention y `TimestampMixin`
- Modelo `App` con UUID PK, enum `AppStore` vinculado al tipo PostgreSQL `app_store_enum`, y constraint único `(bundle_id, store)`
- Modelo `PriceHistory` con PK compuesta `(id, timestamp)`, particionado por `RANGE (timestamp)`, sin FK (limitación de PostgreSQL en tablas particionadas)
- Modelo `Review` con JSONB (`metadata_`), FK a `apps`, índice GIN en metadata e índice compuesto `(app_id, review_date)`
- Configuración completa de Alembic async con `asyncio.run()` y auto-import de modelos
- Migración manual `001`: 25 particiones mensuales (Ene 2026 → Ene 2028) + partición DEFAULT
- Corregido `Settings` con `extra="ignore"` para tolerar variables de entorno no declaradas (ej. `GITHUB_PAT`)
- Suite de 5 tests async verificando inserción, particiones, índices y enum

## Flujo de Trabajo

```
[poetry run alembic upgrade head]
    → Crea enum app_store_enum
    → Crea tabla apps (UUID PK, timestamps, unique constraint)
    → Crea tabla price_history (PARTITION BY RANGE, PK compuesta)
        → 24 particiones mensuales + DEFAULT
        → Índice BRIN en timestamp
        → Índice B-tree (app_id, timestamp DESC)
    → Crea tabla reviews (JSONB metadata, FK → apps)
        → Índice GIN en metadata
        → Índice compuesto (app_id, review_date)
```

**Para verificar:**
```bash
docker compose up -d postgres
poetry run alembic upgrade head
poetry run pytest tests/test_models.py -v
```

## Archivos Afectados

| Archivo | Cambio |
|---------|--------|
| `src/core/database.py` | Nuevo — async engine, session factory, Base, TimestampMixin, get_session() |
| `src/core/config.py` | Modificado — agregado `extra="ignore"` en SettingsConfigDict |
| `src/modules/apps/__init__.py` | Nuevo — exports del módulo (App, AppStore, PriceHistory, Review) |
| `src/modules/apps/models.py` | Nuevo — modelos SQLAlchemy: AppStore enum, App, PriceHistory, Review |
| `alembic.ini` | Nuevo — configuración de Alembic con logging |
| `alembic/env.py` | Nuevo — runner async de migraciones, importa modelos para autogenerate |
| `alembic/script.py.mako` | Nuevo — template de migraciones |
| `alembic/versions/001_initial_schema.py` | Nuevo — migración manual con particiones, BRIN, GIN |
| `tests/__init__.py` | Nuevo — paquete de tests |
| `tests/test_models.py` | Nuevo — 5 tests: insert App, particiones ≥24, GIN, BRIN, enum |
| `.env` | Modificado — agregadas variables DATABASE_URL, REDIS_URL con localhost |

## Notas Técnicas

- **PK compuesta en `price_history`**: PostgreSQL exige que la columna de partición forme parte de cualquier PRIMARY KEY o UNIQUE constraint
- **Sin FK en `price_history`**: PostgreSQL no propaga FK desde tablas particionadas a particiones hijas — la integridad referencial se maneja en capa de aplicación
- **Enum explícito**: `Enum(AppStore, name="app_store_enum", create_type=False)` es obligatorio en `mapped_column`; sin esto, SQLAlchemy genera el nombre en minúsculas del class name (`appstore`) como tipo PostgreSQL
- **Tests con engines separados**: Cada test crea su propio `create_async_engine()` para evitar errores de asyncpg "another operation is in progress" al compartir el pool de conexiones
- **Migración manual**: Alembic no puede autogenerar tablas particionadas ni sus particiones hijas
- **Partición DEFAULT**: Captura datos fuera del rango definido sin errores de inserción
- **`metadata_` como atributo Python**: `metadata` es palabra reservada de `DeclarativeBase`, se usa `metadata_` como alias mapeado a la columna `metadata`
