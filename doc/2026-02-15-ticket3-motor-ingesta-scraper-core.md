# Ticket 3 — Motor de Ingesta (Scraper Core)

**Fecha:** 2026-02-15

## Resumen

Implementacion del motor de scraping asincrono para la plataforma Market Sentinel. Este modulo permite realizar web scraping de tiendas de aplicaciones (Apple App Store y Google Play) con concurrencia controlada, reintentos automaticos con backoff exponencial y parsing HTML estructurado. Incluye integracion con Arq como cola de tareas asincronas y un endpoint REST para disparar scraping bajo demanda.

## Cambios Principales

- Creado modulo `src/modules/scraping/` con cliente HTTP async, parsers HTML y scrapers por tienda
- Implementado `HTTPClient` con rotacion de User-Agent, reintentos via tenacity y manejo de rate limiting (HTTP 429)
- Creados parsers HTML con BeautifulSoup: metadata de app, precios y reviews
- Implementado `BaseScraper` abstracto con `scrape_batch()` usando `asyncio.Semaphore` para concurrencia limitada
- Implementado `AppleStoreScraper` completo con selectores CSS especificos
- Creado esqueleto de `GooglePlayScraper` (pendiente de implementacion)
- Configurado worker Arq con tareas `scrape_app_task` y `scrape_batch_task`
- Agregado endpoint `POST /scrape/{app_id}` que encola trabajos via Redis
- Agregado servicio `worker` en Docker Compose
- Agregados 5 settings configurables para el scraper en `config.py`
- Creados 12 tests unitarios con mocks (sin dependencia de servicios externos)

## Flujo de Trabajo

1. Usuario realiza `POST /scrape/{app_id}` con el ID de una app registrada
2. El endpoint crea un pool Redis y encola un job `scrape_app_task`
3. El worker Arq consume el job y busca la app en la base de datos
4. Segun el store de la app, se selecciona el scraper correspondiente (Apple/Google)
5. El scraper construye la URL, realiza la peticion HTTP y parsea el HTML
6. Los resultados se persisten: metadata de app actualizada, precio en `PriceHistory`, reviews deduplicadas en `Review`

```
[POST /scrape/{app_id}] → [Redis Queue] → [Arq Worker]
    → [DB: get App] → [Select Scraper] → [HTTP GET]
    → [Parse HTML] → [ScrapeResult]
    → [DB: update App + insert Price + insert Reviews]
```

### Scrape en lote

```
[scrape_batch_task(app_ids)] → [Enqueue N scrape_app_task]
    → [Semaphore(concurrency)] → [asyncio.gather] → [Results]
```

## Archivos Afectados

| Archivo | Cambio |
|---------|--------|
| `src/modules/scraping/__init__.py` | Nuevo — Exporta clases principales del modulo |
| `src/modules/scraping/schemas.py` | Nuevo — Schemas Pydantic: ScrapedApp, ScrapedPrice, ScrapedReview, ScrapeResult |
| `src/modules/scraping/client.py` | Nuevo — HTTPClient async con User-Agent dinamico via `fake-useragent`, tenacity retries, manejo 429 |
| `src/modules/scraping/parsers.py` | Nuevo — HTMLParser base, AppMetadataParser, PriceParser, ReviewParser |
| `src/modules/scraping/base.py` | Nuevo — BaseScraper abstracto con scrape_batch() y Semaphore |
| `src/modules/scraping/stores/__init__.py` | Nuevo — Exporta scrapers de tiendas |
| `src/modules/scraping/stores/apple.py` | Nuevo — AppleStoreScraper con selectores CSS para App Store |
| `src/modules/scraping/stores/google.py` | Nuevo — GooglePlayScraper esqueleto (NotImplementedError) |
| `src/worker/__init__.py` | Modificado — WorkerSettings de Arq con funciones, startup/shutdown hooks |
| `src/worker/tasks.py` | Nuevo — scrape_app_task, scrape_batch_task, _save_scrape_result |
| `src/core/config.py` | Modificado — +5 settings del scraper (concurrency, timeout, retries, wait) |
| `src/api/__init__.py` | Modificado — +endpoint POST /scrape/{app_id} con pool Arq Redis |
| `docker-compose.yml` | Modificado — +servicio worker con comando `arq src.worker.WorkerSettings` |
| `.env.example` | Modificado — +variables SCRAPER_CONCURRENCY, SCRAPER_TIMEOUT, etc. |
| `tests/test_scraping.py` | Nuevo — 9 tests: client rotation/retries/429, parsers, apple scraper, batch |
| `tests/test_worker_tasks.py` | Nuevo — 3 tests: save_scrape_result, app_not_found |

## Notas Tecnicas

- **User-Agent rotation**: Se usa la libreria `fake-useragent` para generar User-Agents dinamicos y actualizados (Chrome, Firefox, Safari) en cada request, evitando listas hardcodeadas
- **Retry con tenacity**: Backoff exponencial configurable (min 1s, max 10s) con hasta 3 reintentos por defecto. Solo se reintenta en `TimeoutException` y `RateLimitError`
- **HTTP 429**: Se lee el header `Retry-After`, se loguea un warning y se re-lanza como `RateLimitError` para que tenacity maneje el reintento
- **Concurrencia**: `scrape_batch()` usa `asyncio.Semaphore` (default 50) + `asyncio.gather(return_exceptions=True)` para limitar requests concurrentes
- **Deduplicacion de reviews**: Se verifica por `(app_id, external_review_id)` antes de insertar, evitando duplicados
- **Google Play**: Solo tiene estructura base con `build_url()` implementado; `scrape()` lanza `NotImplementedError` (fuera de scope)
- **Dependencia `fake-useragent`**: Reemplaza la lista estatica de 6 User-Agents por generacion dinamica via `UserAgent(browsers=["Chrome", "Firefox", "Safari"])`, con base de datos actualizable de user agents reales
- **Variables de entorno**: `SCRAPER_CONCURRENCY=50`, `SCRAPER_TIMEOUT=30`, `SCRAPER_MAX_RETRIES=3`, `SCRAPER_RETRY_MIN_WAIT=1.0`, `SCRAPER_RETRY_MAX_WAIT=10.0`
- **Tests**: Todos los tests usan mocks (AsyncMock) para HTTP y DB, no requieren servicios corriendo
