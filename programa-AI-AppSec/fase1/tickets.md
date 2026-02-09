# TICKETS


## Roadmap de Implementación (Backlog Fase 1)

Plan de trabajo de 6 semanas dividido en Sprints lógicos.

### 📅 Semanas 1-2: Fundamentos y Modelado

### 🎫 Ticket 1: Setup de Infraestructura Asíncrona & Docker

- **Objetivo:** Entorno reproducible con Docker Compose.
- **Tareas:**
    - [ ]  Configurar `docker-compose.yml` (Postgres 16, Redis, App).
    - [ ]  Setup de Poetry y Pydantic Settings.
    - [ ]  Configurar Linter (Ruff) y Pre-commit hooks.
- **DoD:** `docker-compose up` levanta sin errores.

### 🎫 Ticket 2: Modelado de DB Avanzado

- **Objetivo:** Esquema SQL resiliente.
- **Tareas:**
    - [ ]  Configurar Alembic Async.
    - [ ]  Implementar Tabla Particionada `price_history`.
    - [ ]  Implementar Tabla `reviews` con JSONB e índices GIN.
- **DoD:** Migraciones aplicadas y verificación de particiones en DB.

### 📅 Semanas 3-4: Ingesta y Lógica

### 🎫 Ticket 3: Motor de Ingesta (Scraper Core)

- **Objetivo:** Worker asíncrono robusto.
- **Tareas:**
    - [ ]  Cliente `httpx` con rotación de User-Agents.
    - [ ]  Lógica de Retries con `tenacity`.
    - [ ]  Parsers de HTML con `BeautifulSoup` para extraer precios y textos.
- **DoD:** Scraping exitoso de 50 URLs concurrentes manejando errores 429.

### 🎫 Ticket 4: Validación & Integridad

- **Objetivo:** Data Quality Firewall.
- **Tareas:**
    - [ ]  Schemas Pydantic v2 para entrada de datos sucios.
    - [ ]  Normalización de monedas y formatos de fecha.
- **DoD:** Tests unitarios fallan ante datos inválidos.

### 🎫 Ticket 5: Procesamiento de Texto con Polars

- **Objetivo:** Preparación para IA (Data Cleaning).
- **Tareas:**
    - [ ]  Pipeline en Polars para limpieza de texto (regex, lowercasing).
    - [ ]  Anonimización de PII básica en reviews.
- **DoD:** Procesamiento de 10k reviews en < 1 segundo.

### 📅 Semanas 5-6: API & Despliegue

### 🎫 Ticket 6: API RESTful High-Performance

- **Objetivo:** Exponer datos al mundo.
- **Tareas:**
    - [ ]  Endpoints FastAPI (`GET /apps`, `GET /history`).
    - [ ]  Implementar Paginación (Cursor-based).
    - [ ]  Documentación OpenAPI (Swagger).
- **DoD:** Response time < 200ms en local.

### 🎫 Ticket 7: Optimización SQL & Vistas Materializadas

- **Objetivo:** Analytics en tiempo real.
- **Tareas:**
    - [ ]  Crear Materialized View para tendencias de precios.
    - [ ]  Optimizar queries con `EXPLAIN ANALYZE`.
- **DoD:** Reducción de tiempo de query compleja en un 50%.

### 🎫 Ticket 8: Observabilidad & Logs

- **Objetivo:** Trazabilidad nivel Lead.
- **Tareas:**
    - [ ]  Implementar `structlog` (JSON logs).
    - [ ]  Añadir Correlation IDs en requests.
- **DoD:** Logs trazables desde API hasta Worker.

### 🎫 Ticket 9: Hardening & Docker Prod

- **Objetivo:** Seguridad de Contenedores.
- **Tareas:**
    - [ ]  Usuario non-root en Dockerfile.
    - [ ]  Escaneo de vulnerabilidades con Trivy.
- **DoD:** Imagen limpia de vulnerabilidades críticas.

---

