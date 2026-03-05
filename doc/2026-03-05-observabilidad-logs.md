# Observabilidad & Logs estructurados con Correlation IDs

**Fecha:** 2026-03-05

## Resumen

Implementación del sistema de observabilidad global para Market Sentinel. Se configura `structlog` con salida JSON estructurada en toda la aplicación y se añade propagación de `Correlation ID` desde cada request HTTP hasta el worker de background, permitiendo trazar el ciclo de vida completo de una operación.

## Cambios Principales

- Creado `src/core/logging.py` con función `setup_logging()` que configura `structlog` globalmente: JSON output, timestamps ISO 8601, merge de contextvars, log level dinámico
- Creado `src/api/middleware.py` con `CorrelationIdMiddleware` (Starlette) que genera o propaga el header `X-Correlation-ID` por request y lo expone en la respuesta
- Modificado `src/api/__init__.py`: llamada a `setup_logging()` al inicio, registro del middleware y extracción del `correlation_id` para pasarlo al job Arq
- Modificado `src/worker/__init__.py`: llamada a `setup_logging()` en `startup()` para que el worker también emita logs JSON
- Modificado `src/worker/tasks.py`: `scrape_app_task` y `scrape_batch_task` aceptan `correlation_id: str | None` y lo bindean al logger para que aparezca en cada línea de log

## Flujo de Trabajo

**Punto de entrada:** Request HTTP al API (cualquier endpoint)

```
[Request HTTP]
  → CorrelationIdMiddleware
      · Lee header X-Correlation-ID o genera UUID
      · clear_contextvars() + bind_contextvars(correlation_id=...)
  → Handler FastAPI
      · Logs incluyen correlation_id automáticamente via merge_contextvars
      · POST /scrape/{app_id}: extrae correlation_id y lo pasa al job Arq
  → Worker Arq (proceso separado)
      · scrape_app_task(ctx, app_id, correlation_id)
      · logger.bind(correlation_id=correlation_id)
      · Todos los logs del worker incluyen el mismo correlation_id
  → [Response HTTP con header X-Correlation-ID]
```

**Resultado:** Cada log line (API + Worker) comparte el mismo `correlation_id`, lo que permite filtrar todos los eventos de una operación concreta en cualquier sistema de agregación de logs (Loki, Datadog, CloudWatch, etc.).

## Archivos Afectados

| Archivo | Cambio |
|---------|--------|
| `src/core/logging.py` | **Nuevo** — función `setup_logging()` con configuración global de structlog |
| `src/api/middleware.py` | **Nuevo** — `CorrelationIdMiddleware` para gestión de Correlation IDs |
| `src/api/__init__.py` | Registro del middleware, llamada a `setup_logging()`, propagación de `correlation_id` al job |
| `src/worker/__init__.py` | Llamada a `setup_logging()` en `startup()` |
| `src/worker/tasks.py` | Parámetro `correlation_id` en `scrape_app_task` y `scrape_batch_task` |

## Notas Técnicas

- `structlog.contextvars` usa `contextvars.ContextVar` de Python, por lo que el contexto es seguro en entornos async (no hay contaminación entre requests concurrentes)
- `clear_contextvars()` al inicio de cada request garantiza que no se filtren datos de requests anteriores reusados por el mismo worker thread
- `cache_logger_on_first_use=True` en la configuración mejora el rendimiento evitando re-resolución de procesadores en cada llamada al logger
- El `correlation_id` se pasa como argumento posicional al job Arq (no como kwarg `_correlation_id`) para compatibilidad con la firma de las tareas
- Los warnings de Pylance sobre imports no resueltos son falsos positivos del entorno de desarrollo; los paquetes están instalados en el virtualenv de Poetry
