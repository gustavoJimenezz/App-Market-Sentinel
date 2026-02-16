# Ticket 5: Procesamiento de Texto con Polars

**Fecha:** 2026-02-16

## Resumen

Implementacion de un pipeline de procesamiento de texto batch usando Polars para limpieza y anonimizacion de PII en reviews de app stores. El modulo prepara los datos textuales para analisis con IA, ejecutando operaciones vectorizadas en Rust para cumplir el objetivo de rendimiento de 10k reviews en menos de 1 segundo.

## Cambios Principales

- Creado modulo `src/modules/text_processing/` con pipeline completo de limpieza y anonimizacion
- Pipeline de limpieza: remocion de HTML, URLs, emojis, lowercasing y normalizacion de espacios
- Anonimizacion de PII: emails, telefonos, tarjetas de credito, SSN y nombres de autores
- Operaciones vectorizadas con Polars (`str.replace_all` nativo en Rust) para alto rendimiento
- Integracion en el worker existente para procesar reviews antes de persistir en BD
- Metadata de calidad almacenada en campo JSONB (`metadata_`) de cada review
- 71 tests nuevos incluyendo benchmark de rendimiento (10k reviews < 1s)

## Flujo de Trabajo

1. El worker recibe un batch de reviews scrapeadas (`list[ScrapedReview]`)
2. Se convierte a un DataFrame de Polars con esquema tipado
3. Se ejecuta la limpieza vectorizada: HTML → URLs → emojis → lowercase → whitespace
4. Se detectan flags de PII en el contenido original (email, CC, SSN)
5. Se anonimiza el texto limpio: regex vectorizados para email/CC/SSN, `map_elements` para nombres
6. Se genera metadata de procesamiento (longitudes, flags de PII detectado)
7. Los resultados se integran al guardar cada Review en la BD

```
[ScrapedReview batch] → [Polars DataFrame] → [Limpieza vectorizada] → [Deteccion PII] → [Anonimizacion] → [Metadata] → [Review + JSONB en BD]
```

## Archivos Afectados

| Archivo | Cambio |
|---------|--------|
| `src/modules/text_processing/__init__.py` | Nuevo modulo, export de `process_reviews_batch` |
| `src/modules/text_processing/patterns.py` | Regex compilados para HTML, URL, emoji, email, phone, CC, SSN |
| `src/modules/text_processing/cleaners.py` | Funciones puras: `remove_html_tags`, `remove_urls`, `remove_emojis`, `normalize_whitespace`, `clean_text` |
| `src/modules/text_processing/anonymizers.py` | Funciones PII: `anonymize_emails`, `anonymize_phones`, `anonymize_credit_cards`, `anonymize_ssn`, `anonymize_author_name`, `anonymize_pii` |
| `src/modules/text_processing/pipeline.py` | Pipeline batch con Polars: construccion de DataFrame, limpieza y anonimizacion vectorizada, generacion de metadata |
| `src/worker/tasks.py` | Integracion: llamada a `process_reviews_batch()` antes de guardar reviews, uso de datos procesados y metadata |
| `tests/test_text_cleaners.py` | 29 tests para funciones de limpieza |
| `tests/test_text_anonymizers.py` | 27 tests para funciones de anonimizacion PII |
| `tests/test_text_pipeline.py` | 15 tests de integracion del pipeline + benchmark de rendimiento |

## Notas Tecnicas

- **Rendimiento**: Las operaciones `.str.replace_all()` de Polars se ejecutan en Rust (vectorizadas), mientras que `map_elements` se usa solo para logica Python compleja (anonimizacion de nombres). Esto permite cumplir el DoD de 10k reviews < 1s
- **Manejo de nulls**: El DataFrame se crea con schema explicito (`pl.Utf8`) para evitar errores cuando todas las filas de una columna son null
- **Orden de anonimizacion**: Credit cards y SSN se anonimizan antes que telefonos para evitar falsos positivos (los patrones de telefono son mas amplios)
- **Fallback**: Si una review no se encuentra en el mapa procesado, se usan los valores originales sin procesar
- **Autor**: Solo se anonimizan iniciales (`"John Doe" → "J. D."`), sin aplicar lowercase para preservar legibilidad
- **Dependencia**: Polars ya estaba en `pyproject.toml` (`^1.20`), no se agregaron dependencias nuevas
