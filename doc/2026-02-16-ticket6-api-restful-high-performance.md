# API RESTful High-Performance con Paginación Cursor-Based

**Fecha:** 2026-02-16

## Resumen

Implementación de una API REST modular que expone los datos almacenados (apps, precios, reviews) a través de endpoints con paginación cursor-based, filtros avanzados y modelos de respuesta tipados. Transforma la API de 2 endpoints básicos a una interfaz completa con documentación OpenAPI autogenerada.

## Cambios Principales

- Creados 3 routers modulares: apps, prices y reviews con filtros específicos por dominio
- Implementada paginación cursor-based usando base64 sobre tupla `(sort_value, UUID)` — estable ante inserciones concurrentes
- Agregados modelos de respuesta Pydantic con `from_attributes=True` para serialización directa desde SQLAlchemy
- Modelo genérico `PaginatedResponse[T]` reutilizable en todos los endpoints
- Metadata OpenAPI añadida a la app FastAPI (descripción, versión, tags por dominio)
- Excepción de regla B008 para routers FastAPI en configuración de ruff
- 16 tests de integración con `httpx.AsyncClient` y dependency override para DB

## Flujo de Trabajo

1. El cliente envía una petición GET con filtros opcionales y cursor de paginación
2. El router construye la query SQLAlchemy aplicando filtros como `WHERE` clauses
3. Si hay cursor, se decodifica de base64 y se aplica como condición `(sort_col, id) < (cursor_val, cursor_id)`
4. Se ejecuta `LIMIT N+1` para detectar si hay más páginas sin hacer `COUNT(*)`
5. Se construye la respuesta con items serializados, `next_cursor` y `has_more`

```
[Request + Filtros + Cursor] → [Query Builder] → [LIMIT+1 Fetch] → [PaginatedResponse]
```

### Endpoints Implementados

| Método | Ruta | Filtros |
|--------|------|---------|
| `GET` | `/apps` | `store`, `is_active`, `name` (ILIKE) |
| `GET` | `/apps/{app_id}` | — (404 si no existe) |
| `GET` | `/prices/history` | `app_id` (requerido), `date_from`, `date_to`, `currency`, `region` |
| `GET` | `/reviews` | `app_id` (requerido), `rating_min`, `rating_max`, `date_from`, `date_to` |

## Archivos Afectados

| Archivo | Cambio |
|---------|--------|
| `src/api/schemas.py` | Modelos Pydantic: `AppResponse`, `PriceHistoryResponse`, `ReviewResponse`, `PaginatedResponse[T]` |
| `src/api/dependencies.py` | `PaginationParams`, `encode_cursor()`, `decode_cursor()` |
| `src/api/routers/__init__.py` | Init del paquete de routers |
| `src/api/routers/apps.py` | Router de apps: listado con filtros y detalle por ID |
| `src/api/routers/prices.py` | Router de precio histórico con filtros temporales y monetarios |
| `src/api/routers/reviews.py` | Router de reviews con filtros de rating y fecha |
| `src/api/__init__.py` | Metadata OpenAPI, tags en endpoints existentes, inclusión de routers |
| `pyproject.toml` | Excepción B008 para routers FastAPI |
| `tests/test_api_endpoints.py` | 16 tests de integración (lista vacía, con datos, filtros, 404, 422, paginación) |

## Notas Técnicas

- **Paginación cursor-based vs offset:** El cursor es estable ante inserciones concurrentes y no degrada con páginas profundas. Se codifica como `base64("{isoformat_timestamp}:{uuid}")`
- **LIMIT+1:** Se piden N+1 filas para detectar `has_more` sin ejecutar un `COUNT(*)` adicional
- **Orden consistente:** Todos los sort usan dirección uniforme (`DESC, DESC`) porque la comparación de tuplas `<` requiere que ambas columnas tengan la misma dirección de ordenamiento
- **Dependency override en tests:** Los tests inyectan un engine fresco por test vía `app.dependency_overrides[get_session]` para evitar conflictos de event loop con asyncpg
- **Índices aprovechados:** `(app_id, timestamp DESC)` en `price_history`, `(app_id, review_date)` en `reviews`
