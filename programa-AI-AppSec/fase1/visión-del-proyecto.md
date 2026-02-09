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


## 5. Estructura del Repositorio

Plaintext

app-market-sentinel/
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
└── README.md             # Este documento