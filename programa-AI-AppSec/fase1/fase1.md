# FASE 1

**App Market Sentinel**. Este proyecto no es solo un scraper; es un sistema de **Data Engineering** diseñado para ser la base de una IA, aprovechando tu experiencia en **Onapsis** , tu dominio de **Asyncio** y tu reciente graduación en la **UNLZ**.

---

### 1) Descripción del Proyecto

El **App Market Sentinel** es un motor de ingesta asíncrona que monitorea precios de suscripciones y feedback de usuarios en tiendas de aplicaciones (App Store/Play Store). Sirve para que empresas de software realicen inteligencia competitiva automatizada. Maneja datos estructurados (precios, versiones) y no estructurados (reviews, changelogs en JSONB). Produce un histórico normalizado, métricas de sentimiento y alertas de cambios de precios, exponiendo todo mediante una API de alto rendimiento.

### 2) Casos de Uso (Features)

1. 
    
    **Ingesta Multi-Store:** Scraping asíncrono de Apple App Store y Google Play Store.
    
2. **Tracking de Suscripciones:** Registro histórico de cambios en los planes de pago.
3. 
    
    **Parser de Changelogs:** Segmentación de actualizaciones para detectar nuevas features.
    
4. 
    
    **Sentiment Analytics:** Preparación de reviews para análisis de sentimiento masivo.
    
5. **Endpoint de Comparativa:** `/api/v1/compare?apps=id1,id2` para ver tendencias cruzadas.
6. 
    
    **Dashboard de Telemetría:** Pantalla de FastAPI (Swagger) para monitorear la salud del pipeline.
    
7. **Alertas de Churn:** Detección de picos de reviews negativas tras una subida de precio.
8. 
    
    **Búsqueda Semántica:** Endpoints que aprovechan índices GIN sobre JSONB para buscar fallos técnicos.
    
9. 
    
    **Exportación de Datasets:** Descarga de datos limpios en CSV/JSON vía Polars.
    
10. 
    
    **Admin Panel:** Gestión de apps a monitorear (CRUD).
    

### 3) Reglas de Negocio

- **Cambio de Precio:** Se define cuando el valor extraído difiere del último registro en la tabla `price_history` para una misma región/moneda.
- **Detección de Oferta:** Cambio de precio negativo > 15% respecto al promedio de los últimos 30 días.
- **Fallo de Scraping:** Tras 3 reintentos fallidos, se marca la app como "Sync Error" y se dispara una alerta a los logs.
- 
    
    **Límites de Usuario:** Máximo 100 consultas por minuto (Rate Limit) por IP.
    
- **Retención:** Datos de precios se guardan por 2 años (particionados); reviews crudas se archivan tras 6 meses.

### 4) Requerimientos Técnicos

- 
    
    **Funcionales:** Ingesta asíncrona, almacenamiento relacional, API RESTful, validación de esquemas.
    
- 
    
    **No Funcionales:** Latencia de API < 200ms, soporte para 10k reviews/seg en procesamiento (Polars) , aislamiento de datos (RLS).
    
- 
    
    **Observabilidad:** Logs estructurados (JSON), métricas de éxito/error de scraping, alertas de CPU/RAM del worker.
    

### 5) Arquitectura Recomendada

Plaintext

`[Scraper Workers (Asyncio)] --(Redis Queue)--> [PostgreSQL (pgvector + JSONB)]
      ^                                               |
[Scheduler (Cron)]                            [FastAPI (Async SQLAlchemy)]
      |                                               |
[External Stores APIs/HTML]                   [Frontend / Consumers]`

- **Background:** El scraping y el procesamiento pesado con Polars.
- **DB:** Todo el histórico y fragmentos de texto.
- **Cache:** Resultados de analíticas frecuentes en Redis.

### 6) Modelo de Datos (PostgreSQL)

- **`apps`**: `id (PK)`, `name`, `bundle_id`, `store (enum)`.
- **`price_history`**: `id`, `app_id (FK)`, `price (numeric)`, `currency`, `timestamp (index)`.
- **`reviews`**: `id`, `app_id (FK)`, `content (text)`, `metadata (jsonb)`, `vector_embedding (vector)`.
- **Índices:** `GIN(metadata)` para las reviews, `BRIN(timestamp)` para precios.
- **Query Típica:** `SELECT app_id, AVG(price) OVER(PARTITION BY app_id ORDER BY timestamp) FROM price_history;`

### 7) Pipeline de Ingesta

- **Estrategia:** Rotación de `User-Agent` y uso de proxies si es necesario.
- **Anti-bot:** Respeto de `robots.txt` y delays aleatorios (Jitter).
- 
    
    **Normalización:** Pydantic v2 mapea los campos de Apple y Google a un modelo único `UniversalAppModel`.
    

### 8) Roadmap por Fases

- 
    
    **Fase 0:** Setup con Docker, Alembic y Pytest.
    
- 
    
    **Fase 1 (MVP):** Scraper para 1 app de la Play Store persistiendo en Postgres.
    
- **Fase 2:** Soporte App Store, manejo de errores y reintentos (Celery/Redis).
- **Fase 3:** Vistas materializadas para promedios y dashboard básico.
- 
    
    **Fase 4:** Integración de `pgvector` para agrupar reviews similares.
    

### 9) Testing

- 
    
    **Unitarios:** Validación de modelos Pydantic.
    
- 
    
    **Integración:** Test de flujo completo: Scraper Mock -> DB -> API.
    
- **Scraper:** Tests de regresión sobre HTML estático guardado.
- **Reglas:** Test de detección de ofertas con datos falsos.

### 10) Plan de Deployment

- 
    
    **Infra:** Docker Compose para desarrollo.
    
- 
    
    **Prod:** VPS (Hetzner/DigitalOcean) o Railway para el backend.
    
- 
    
    **Variables:** `DATABASE_URL`, `REDIS_URL`, `API_KEYS` (en `.env` no trackeado).
    

### 11) Seguridad Mínima

- 
    
    **Auth:** JWT para endpoints de escritura.
    
- **DB:** Row Level Security (RLS) para prevenir que usuarios vean monitoreos ajenos.
- 
    
    **Sanitización:** Uso obligatorio de SQLAlchemy para evitar SQL Injection.
    

### 12) Plan de Negocio (Contexto)

- **Target:** Managers de Producto y Desarrolladores Indie.
- **Monetización:** SaaS Freemium, API para empresas, Reportes semanales por suscripción.
- **Competencia:** AppAnnie, SensorTower (pero el tuyo es Open Source y personalizable).

### 13) Extras para CV/GitHub

- 
    
    **README:** Incluir diagrama de arquitectura (Mermaid.js) y guía de setup rápido.
    
- 
    
    **CI/CD:** GitHub Actions para correr Pytest automáticamente.
    
- 
    
    **Screenshots:** Evidencia de la API documentada con Swagger.
    

**App Market Sentinel**. Este proyecto no es solo un scraper; es un sistema de **Data Engineering** diseñado para ser la base de una IA, aprovechando tu experiencia en **Onapsis** , tu dominio de **Asyncio** y tu reciente graduación en la **UNLZ**.

---

### 1) Descripción del Proyecto

El **App Market Sentinel** es un motor de ingesta asíncrona que monitorea precios de suscripciones y feedback de usuarios en tiendas de aplicaciones (App Store/Play Store). Sirve para que empresas de software realicen inteligencia competitiva automatizada. Maneja datos estructurados (precios, versiones) y no estructurados (reviews, changelogs en JSONB). Produce un histórico normalizado, métricas de sentimiento y alertas de cambios de precios, exponiendo todo mediante una API de alto rendimiento.

### 2) Casos de Uso (Features)

1. 
    
    **Ingesta Multi-Store:** Scraping asíncrono de Apple App Store y Google Play Store.
    
2. **Tracking de Suscripciones:** Registro histórico de cambios en los planes de pago.
3. 
    
    **Parser de Changelogs:** Segmentación de actualizaciones para detectar nuevas features.
    
4. 
    
    **Sentiment Analytics:** Preparación de reviews para análisis de sentimiento masivo.
    
5. **Endpoint de Comparativa:** `/api/v1/compare?apps=id1,id2` para ver tendencias cruzadas.
6. 
    
    **Dashboard de Telemetría:** Pantalla de FastAPI (Swagger) para monitorear la salud del pipeline.
    
7. **Alertas de Churn:** Detección de picos de reviews negativas tras una subida de precio.
8. 
    
    **Búsqueda Semántica:** Endpoints que aprovechan índices GIN sobre JSONB para buscar fallos técnicos.
    
9. 
    
    **Exportación de Datasets:** Descarga de datos limpios en CSV/JSON vía Polars.
    
10. 
    
    **Admin Panel:** Gestión de apps a monitorear (CRUD).
    

### 3) Reglas de Negocio

- **Cambio de Precio:** Se define cuando el valor extraído difiere del último registro en la tabla `price_history` para una misma región/moneda.
- **Detección de Oferta:** Cambio de precio negativo > 15% respecto al promedio de los últimos 30 días.
- **Fallo de Scraping:** Tras 3 reintentos fallidos, se marca la app como "Sync Error" y se dispara una alerta a los logs.
- 
    
    **Límites de Usuario:** Máximo 100 consultas por minuto (Rate Limit) por IP.
    
- **Retención:** Datos de precios se guardan por 2 años (particionados); reviews crudas se archivan tras 6 meses.

### 4) Requerimientos Técnicos

- 
    
    **Funcionales:** Ingesta asíncrona, almacenamiento relacional, API RESTful, validación de esquemas.
    
- 
    
    **No Funcionales:** Latencia de API < 200ms, soporte para 10k reviews/seg en procesamiento (Polars) , aislamiento de datos (RLS).
    
- 
    
    **Observabilidad:** Logs estructurados (JSON), métricas de éxito/error de scraping, alertas de CPU/RAM del worker.
    

### 5) Arquitectura Recomendada

Plaintext

`[Scraper Workers (Asyncio)] --(Redis Queue)--> [PostgreSQL (pgvector + JSONB)]
      ^                                               |
[Scheduler (Cron)]                            [FastAPI (Async SQLAlchemy)]
      |                                               |
[External Stores APIs/HTML]                   [Frontend / Consumers]`

- **Background:** El scraping y el procesamiento pesado con Polars.
- **DB:** Todo el histórico y fragmentos de texto.
- **Cache:** Resultados de analíticas frecuentes en Redis.

### 6) Modelo de Datos (PostgreSQL)

- **`apps`**: `id (PK)`, `name`, `bundle_id`, `store (enum)`.
- **`price_history`**: `id`, `app_id (FK)`, `price (numeric)`, `currency`, `timestamp (index)`.
- **`reviews`**: `id`, `app_id (FK)`, `content (text)`, `metadata (jsonb)`, `vector_embedding (vector)`.
- **Índices:** `GIN(metadata)` para las reviews, `BRIN(timestamp)` para precios.
- **Query Típica:** `SELECT app_id, AVG(price) OVER(PARTITION BY app_id ORDER BY timestamp) FROM price_history;`

### 7) Pipeline de Ingesta

- **Estrategia:** Rotación de `User-Agent` y uso de proxies si es necesario.
- **Anti-bot:** Respeto de `robots.txt` y delays aleatorios (Jitter).
- 
    
    **Normalización:** Pydantic v2 mapea los campos de Apple y Google a un modelo único `UniversalAppModel`.
    

### 8) Roadmap por Fases

- 
    
    **Fase 0:** Setup con Docker, Alembic y Pytest.
    
- 
    
    **Fase 1 (MVP):** Scraper para 1 app de la Play Store persistiendo en Postgres.
    
- **Fase 2:** Soporte App Store, manejo de errores y reintentos (Celery/Redis).
- **Fase 3:** Vistas materializadas para promedios y dashboard básico.
- 
    
    **Fase 4:** Integración de `pgvector` para agrupar reviews similares.
    

### 9) Testing

- 
    
    **Unitarios:** Validación de modelos Pydantic.
    
- 
    
    **Integración:** Test de flujo completo: Scraper Mock -> DB -> API.
    
- **Scraper:** Tests de regresión sobre HTML estático guardado.
- **Reglas:** Test de detección de ofertas con datos falsos.

### 10) Plan de Deployment

- 
    
    **Infra:** Docker Compose para desarrollo.
    
- 
    
    **Prod:** VPS (Hetzner/DigitalOcean) o Railway para el backend.
    
- 
    
    **Variables:** `DATABASE_URL`, `REDIS_URL`, `API_KEYS` (en `.env` no trackeado).
    

### 11) Seguridad Mínima

- 
    
    **Auth:** JWT para endpoints de escritura.
    
- **DB:** Row Level Security (RLS) para prevenir que usuarios vean monitoreos ajenos.
- 
    
    **Sanitización:** Uso obligatorio de SQLAlchemy para evitar SQL Injection.
    

### 12) Plan de Negocio (Contexto)

- **Target:** Managers de Producto y Desarrolladores Indie.
- **Monetización:** SaaS Freemium, API para empresas, Reportes semanales por suscripción.
- **Competencia:** AppAnnie, SensorTower (pero el tuyo es Open Source y personalizable).

### 13) Extras para CV/GitHub

- 
    
    **README:** Incluir diagrama de arquitectura (Mermaid.js) y guía de setup rápido.
    
- 
    
    **CI/CD:** GitHub Actions para correr Pytest automáticamente.
    
- 
    
    **Screenshots:** Evidencia de la API documentada con Swagger.
