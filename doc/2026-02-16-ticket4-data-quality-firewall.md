# Ticket 4 — Validación & Integridad (Data Quality Firewall)

**Fecha:** 2026-02-16

## Resumen

Implementación de un firewall de calidad de datos que valida y normaliza toda la información proveniente del scraping antes de persistirla en base de datos. Se agregaron validadores Pydantic a los 4 schemas existentes y funciones puras de normalización para moneda y timestamps, usando enfoque TDD con 47 tests.

## Cambios Principales

- Creado módulo `normalizers.py` con funciones puras de normalización (moneda y timezone)
- Agregados `field_validator` a los 4 schemas Pydantic (`ScrapedApp`, `ScrapedPrice`, `ScrapedReview`, `ScrapeResult`)
- Creados 47 tests TDD organizados en 6 clases de prueba
- Definidas constantes de límites de BD alineadas con las columnas del modelo SQLAlchemy
- Sin dependencias nuevas — solo se usan `pydantic.field_validator` y stdlib

## Flujo de Trabajo

1. El scraper genera datos crudos desde HTML (parsers existentes)
2. Los datos se pasan a los schemas Pydantic (`ScrapedApp`, `ScrapedPrice`, etc.)
3. Los `field_validator` interceptan cada campo antes de crear la instancia:
   - **Strings**: strip de whitespace, validación non-empty en campos requeridos, límite de longitud según columna de BD
   - **Moneda**: normalización de símbolo (`$`→`USD`, `€`→`EUR`) o código lowercase (`usd`→`USD`), rechazo de códigos inválidos
   - **Timestamps**: asignación automática de UTC a datetimes naive
   - **Numéricos**: validación de rangos (precio ≥ 0, rating 1-5, precio ≤ Numeric(10,2))
4. Si la validación falla, se lanza `ValidationError` antes de llegar a `_save_scrape_result()`

```
[HTML crudo] → [Parsers] → [Schemas + Validators] → [_save_scrape_result()] → [PostgreSQL]
                                    ↓ (falla)
                             ValidationError
```

## Archivos Afectados

| Archivo | Cambio |
|---------|--------|
| `src/modules/scraping/normalizers.py` | **Creado** — `normalize_currency()`, `ensure_timezone_aware()`, mapas de símbolos y códigos ISO 4217 |
| `src/modules/scraping/schemas.py` | **Modificado** — Agregados `field_validator` a los 4 schemas, constantes de límites de BD, helpers `_strip_or_none` y `_validate_max_length` |
| `tests/test_validation.py` | **Creado** — 47 tests en 6 clases: `TestNormalizeCurrency`, `TestEnsureTimezoneAware`, `TestScrapedAppValidation`, `TestScrapedPriceValidation`, `TestScrapedReviewValidation`, `TestScrapeResultValidation` |

## Notas Técnicas

- Los validadores usan `mode="before"` para strip/normalización y `mode="after"` para validación de rangos y longitudes, garantizando que la normalización ocurre antes de la validación
- `normalize_currency()` soporta ~15 símbolos de moneda y ~46 códigos ISO 4217 relevantes para app stores
- Los límites de longitud (`_MAX_NAME=255`, `_MAX_ICON_URL=512`, etc.) están alineados con las columnas VARCHAR del modelo SQLAlchemy en `models.py`
- `developer_name` vacío o whitespace-only se convierte en `None` (campo opcional) en lugar de lanzar error
- Los tests existentes de scraping y worker no se vieron afectados porque ya usaban datos válidos
