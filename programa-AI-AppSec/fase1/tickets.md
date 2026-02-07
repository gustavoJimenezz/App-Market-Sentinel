# TICKETS

# 🛡️ App Market Sentinel

> **Intelligent SaaS & App Store Analytics Platform**
> 
> 
> *Data Engineering Pipeline & Market Intelligence Engine*
> 

## 1. Visión del Proyecto

**App Market Sentinel** es un sistema de ingeniería de datos de alto rendimiento diseñado para la ingesta, normalización y análisis de inteligencia competitiva en tiendas de aplicaciones y plataformas SaaS.

A diferencia de un scraper tradicional, este sistema implementa una arquitectura orientada a eventos, capaz de manejar series temporales de precios (Financial Data) y grandes volúmenes de texto no estructurado (Reviews/Changelogs), preparando la infraestructura de datos para modelos de **Inteligencia Artificial (RAG)**.

### 🎯 Objetivos Técnicos (Fase 1)

1. **Ingesta Asíncrona:** Crawling concurrente de alta eficiencia sin bloqueos (Non-blocking I/O).
2. **Integridad de Datos:** Normalización estricta de fuentes heterogéneas (App Store vs Play Store) usando validación de esquemas.
3. **Advanced SQL:** Uso de particionamiento, índices GIN para JSONB y Vistas Materializadas en PostgreSQL.
4. **AI-Readiness:** Limpieza y segmentación de texto (Chunking) lista para vectorización.

---

## 2. Arquitectura del Sistema

El sistema sigue un patrón de **Modular Monolith** con separación estricta entre la API (lectura/gestión) y los Workers (escritura/procesamiento pesado).

### Diagrama de Contenedores

Fragmento de código

`graph TD
    User((Cliente)) -->|REST API| API[FastAPI Backend]
    API -->|Read/Write| DB[(PostgreSQL 16)]
    API -->|Dispatch Jobs| Redis[(Redis Queue)]
    
    Worker[Worker Async - Arq] -->|Consume Jobs| Redis
    Worker -->|Scraping (Httpx)| Web((Fuentes Externas))
    Worker -->|Batch Processing (Polars)| DB
    
    DB -.->|Store Embeddings| PgVector`

### Componentes Core

| **Componente** | **Tecnología** | **Responsabilidad** |
| --- | --- | --- |
| **API Server** | FastAPI + Uvicorn | Endpoints REST, validación de entrada, gestión de usuarios. |
| **Ingestion Engine** | Python Asyncio + Httpx | Scraping concurrente, rotación de proxies, manejo de retries. |
| **Data Processor** | Polars (Rust-backed) | Limpieza de texto masiva, normalización de precios, detección de PII. |
| **Task Queue** | Arq + Redis | Orquestación de trabajos en background. |
| **Storage** | PostgreSQL 16 | Almacenamiento relacional (Precios), Documental (Reviews JSONB) y Vectorial. |

---

## 3. Stack Tecnológico & Decisiones (ADR)

Selección de herramientas basada en performance, tipado estricto y seguridad.

- **Lenguaje:** `Python 3.12+` (Tipado fuerte, features modernas de Asyncio).
- **Web Framework:** `FastAPI` (Estándar de industria para Data APIs).
- **Database:** `PostgreSQL 16` + `pgvector`.
    - *Decisión:* Uso de **JSONB** para flexibilidad en metadatos de reviews y **Partitioning** para el histórico de precios (Time-Series).
- **ORM:** `SQLAlchemy 2.0 (Async)`. Patrón Repository para abstracción de datos.
- **Validación:** `Pydantic v2`. Validación de esquemas en tiempo de ejecución (Rust core).
- **Gestión de Entorno:** `Docker Compose` + `Poetry` (Dependency locking).
- **Testing:** `Pytest` + `Testcontainers` (Pruebas de integración reales).

---

## 4. Modelo de Datos (Schema Design)

El esquema está optimizado para consultas analíticas y búsqueda de texto.

### Tablas Principales

1. **`apps` (Master Data):**
    - `id` (UUID), `bundle_id`, `platform` (Enum), `developer_id`.
2. **`price_history` (Time-Series):**
    - *Particionada por rango de fecha (Mensual).*
    - `app_id`, `price` (Decimal), `currency`, `timestamp` (BRIN Index).
3. **`reviews` (Unstructured Data):**
    - `app_id`, `rating`, `content` (Text), `metadata` (JSONB).
    - *Índice:* **GIN** sobre `metadata` para búsquedas rápidas (ej: versión del dispositivo).
    - *Vector:* Columna `embedding` (vector(1536)) preparada para Fase 2.

---

## 5. Roadmap de Implementación (Backlog Fase 1)

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

## 6. Estructura del Repositorio

Plaintext

`app-market-sentinel/
├── .github/workflows/    # CI/CD (Tests, Linting)
├── docker/               # Configuración de contenedores
├── src/
│   ├── api/              # FastAPI Application
│   ├── core/             # Configuración, DB Session, Logging
│   ├── modules/          # Dominios (Apps, Scraping, Analytics)
│   └── worker/           # Background Workers (Arq)
├── tests/                # Pytest (Unit & Integration)
├── alembic/              # Migraciones de DB
├── docker-compose.yml
├── pyproject.toml        # Dependencias
└── README.md             # Este documento`
