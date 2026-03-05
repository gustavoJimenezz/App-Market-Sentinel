# Ticket 7: Optimización SQL & Vistas Materializadas

**Fecha:** 2026-03-05

## Resumen

Implementación de analytics de tendencias de precios en tiempo real mediante una Materialized View de PostgreSQL (`price_trends`), eliminando el costo de agregación en cada consulta. El objetivo principal es reducir el tiempo de queries complejas en un 50% pre-calculando agregaciones semanales (min, max, promedio) sobre la tabla `price_history`.

## Cambios Principales

- Creada migración Alembic `002` que genera la vista materializada `price_trends` con dos índices (único y de ordenación)
- Añadido modelo read-only `PriceTrend` en SQLAlchemy mapeado a la vista materializada
- Añadido schema de respuesta `PriceTrendResponse` para el endpoint de analytics
- Implementada tarea Arq `refresh_price_trends` que ejecuta `REFRESH MATERIALIZED VIEW CONCURRENTLY`
- Registrada la nueva tarea en `WorkerSettings.functions`
- Creado router `GET /analytics/price-trends` con filtros y paginación cursor-based
- 14 tests de integración y unitarios cubriendo: existencia de la MV, índices, endpoint, paginación y tarea de refresh

## Flujo de Trabajo

### Flujo de datos (escritura y refresh)

```
[Scraper] → [price_history (filas crudas)] → [refresh_price_trends task]
                                                         ↓
                                          REFRESH MATERIALIZED VIEW CONCURRENTLY
                                                         ↓
                                              [price_trends (pre-agregado)]
```

### Flujo de consulta (lectura)

```
[GET /analytics/price-trends?app_id=...] → [Router analytics]
                                                    ↓
                                      SELECT FROM price_trends (MV)
                                                    ↓
                                      [PaginatedResponse[PriceTrendResponse]]
```

**Punto de entrada:** `GET /analytics/price-trends` con parámetro obligatorio `app_id`

**Proceso:** La query lee directamente de `price_trends` (ya pre-agregada por semana). Opcionalmente filtra por `currency`, `region`, `week_from` y `week_to`. La paginación es cursor-based usando el campo `week` como valor de ordenación.

**Resultado:** Lista paginada de tendencias semanales por app, con precio mínimo, máximo, promedio y cantidad de muestras por semana.

### Flujo de refresh

**Punto de entrada:** Tarea Arq `refresh_price_trends` (se encola tras cada batch de scraping o de forma programada)

**Proceso:** Ejecuta `REFRESH MATERIALIZED VIEW CONCURRENTLY price_trends`. La opción `CONCURRENTLY` permite que las lecturas no se bloqueen durante el refresh. Requiere el índice único `ix_price_trends_pk`.

**Resultado:** La vista materializada queda actualizada con todos los datos nuevos de `price_history`.

## Archivos Afectados

| Archivo | Cambio |
|---------|--------|
| `alembic/versions/002_materialized_views.py` | Nueva migración: crea MV `price_trends` + índices `ix_price_trends_pk` y `ix_price_trends_app_id_week` |
| `src/modules/apps/models.py` | Nuevo modelo `PriceTrend` (read-only, mapeado a la MV) |
| `src/api/schemas.py` | Nuevo schema `PriceTrendResponse` |
| `src/worker/tasks.py` | Nueva tarea `refresh_price_trends` |
| `src/worker/__init__.py` | Registra `refresh_price_trends` en `WorkerSettings.functions` |
| `src/api/routers/analytics.py` | Nuevo router `GET /analytics/price-trends` con paginación y filtros |
| `src/api/__init__.py` | Registra `analytics.router` en la app FastAPI |
| `tests/test_analytics.py` | 14 tests: existencia de MV e índices, endpoint, paginación, tarea |

## Notas Técnicas

- **`REFRESH CONCURRENTLY`** requiere que exista un índice único sobre la MV. Se creó `ix_price_trends_pk` sobre `(app_id, currency, region, week)` para cumplir este requisito.
- **El modelo `PriceTrend` es read-only** — no tiene `__table_args__` de constraints ni se usa para INSERT/UPDATE. SQLAlchemy lo trata como una tabla normal a nivel de lectura.
- **Consistencia eventual:** la MV no refleja datos en tiempo real; se actualiza en cada refresh. Para analytics de tendencias semanales esto es aceptable.
- **Paginación:** el cursor usa el campo `week` como valor de ordenación (`week DESC`). A diferencia de otros routers, aquí no se necesita un ID secundario en el cursor porque `(app_id, currency, region, week)` ya es único.
- **Granularidad:** la agregación es semanal (`date_trunc('week', timestamp)`). Si en el futuro se necesita granularidad diaria o mensual, se puede añadir una segunda MV sin modificar la existente.
