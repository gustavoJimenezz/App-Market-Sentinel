# Notas técnicas — Market Sentinel

## ¿Qué es un objeto de PostgreSQL?

### Primero: ¿qué es PostgreSQL?

PostgreSQL es un **sistema gestor de base de datos**. Su trabajo es guardar información de forma organizada y permitirte consultarla, modificarla y borrarla de manera eficiente.

Cuando creas una base de datos en PostgreSQL, no solo tienes tablas. PostgreSQL te da una "caja de herramientas" con distintas estructuras que puedes crear según lo que necesites. A esas estructuras se les llama **objetos**.

### ¿Qué es un objeto?

Un objeto es simplemente **cualquier cosa que creas dentro de la base de datos y que tiene un nombre**.

Igual que en un proyecto de código tienes archivos, funciones y clases (y cada uno tiene su propósito) — en PostgreSQL tienes objetos, y cada tipo resuelve un problema distinto.

Todos los objetos comparten estas características:
- Se crean con `CREATE <tipo> <nombre>`
- Se eliminan con `DROP <tipo> <nombre>`
- Tienen un nombre único dentro de su contexto
- Puedes controlar quién tiene acceso a ellos

### Los objetos más importantes y para qué sirven

**TABLE** — el más básico. Es donde viven los datos. Sin tablas no hay nada.
```
apps, price_history, reviews  → son tablas en este proyecto
```

**INDEX** — no guarda datos nuevos, sino que crea un "mapa" sobre una columna para que las búsquedas sean más rápidas. Sin índice, PostgreSQL lee toda la tabla fila por fila. Con índice, salta directo al dato.
```
Buscar reviews por app_id sin índice → escanea 1 millón de filas
Buscar reviews por app_id con índice → va directo a las 50 filas que importan
```

**VIEW** — es un alias con nombre para una query. No guarda datos, solo guarda la consulta. Cada vez que la usas, ejecuta la query en ese momento.
```sql
CREATE VIEW apps_activas AS SELECT * FROM apps WHERE is_active = true;
-- Cada vez que consultas apps_activas, corre el SELECT en tiempo real
```

**MATERIALIZED VIEW** — igual que una View, pero sí guarda los datos en disco. La query se ejecuta una vez, el resultado queda guardado, y lo sirve directamente sin recalcular. Se actualiza cuando tú lo indicas.

**FUNCTION** — lógica que vive dentro de la base de datos. En vez de calcular algo en Python y luego guardarlo, la función lo calcula directamente en PostgreSQL.

**TRIGGER** — una acción automática que se dispara cuando ocurre algo en la base de datos (un INSERT, UPDATE o DELETE). Por ejemplo: "cada vez que se inserte un precio, actualiza el promedio".

**TYPE** — un tipo de dato personalizado. En este proyecto `app_store_enum` es un TYPE: le dice a PostgreSQL que una columna solo puede tener los valores `APPLE_APP_STORE` o `GOOGLE_PLAY_STORE`.

**SEQUENCE** — generador de valores numéricos incrementales. Se usa internamente para los IDs autoincrementales.

### La idea central

No todo se resuelve con tablas. PostgreSQL te da distintas herramientas porque distintos problemas tienen distintas soluciones óptimas:

| Problema | Solución |
|----------|----------|
| Datos lentos de buscar | `INDEX` |
| Query compleja que repites mucho | `VIEW` |
| Query compleja y lenta que necesita ir rápido | `MATERIALIZED VIEW` |
| Lógica que debe correr automáticamente | `TRIGGER` o `FUNCTION` |
| Columna que solo acepta valores predefinidos | `TYPE` (enum) |

En el contexto de este proyecto, el Ticket 7 introduce un nuevo objeto: una **Materialized View** llamada `price_trends`.

---

## Materialized View: ¿Concepto o Estrategia?

Es **ambas cosas** — un concepto de base de datos que se usa como estrategia de optimización.

### El Concepto

Una **Materialized View** (Vista Materializada) es un objeto de PostgreSQL que guarda físicamente el resultado de una query SQL en disco, como si fuera una tabla normal.

A diferencia de una **View normal** (que es solo un alias de una query y se recalcula cada vez que la consultas), la Materialized View:

- **Pre-calcula** el resultado una vez
- **Lo almacena** en disco
- **Lo sirve directamente** sin recalcular nada
- Se **actualiza manualmente** con `REFRESH MATERIALIZED VIEW`

### La Estrategia (por qué la usamos aquí)

El problema concreto en Market Sentinel:

```
price_history (tabla particionada)
│
├── Millones de filas por app
├── Datos crudos: (app_id, timestamp, price, currency, region)
└── Query de tendencia: GROUP BY + AVG + MIN + MAX + date_trunc
                        → costosa, recalcula todo cada vez
```

La estrategia es **mover el costo del cómputo del momento de la lectura al momento del refresh**:

```
ANTES (sin MV):
  Request → PostgreSQL agrupa millones de filas → respuesta en ~500ms

DESPUÉS (con MV):
  Refresh (offline, en worker) → PostgreSQL pre-agrega todo → guarda en price_trends
  Request → PostgreSQL lee ~100 filas ya agrupadas → respuesta en ~10ms
```

### La Analogía

Piénsalo como un **reporte pre-generado** vs. generarlo en vivo:

- **View normal** = calcular todas las fórmulas cada vez que alguien pide el reporte
- **Materialized View** = tener el reporte ya calculado guardado, y actualizarlo una vez por hora

### Trade-off clave

| Aspecto | Sin MV | Con MV |
|---------|--------|--------|
| Frescura de datos | Tiempo real (100%) | Eventual (depende del refresh) |
| Velocidad de lectura | Lenta (agrega en vivo) | Muy rápida (lee pre-agregado) |
| Costo de escritura | Ninguno extra | Refresh periódico |

Para analytics de tendencias de precios (que no necesitan el precio del último segundo), la consistencia eventual es aceptable y el gain de performance es enorme. Por eso es la estrategia correcta para el Ticket 7.
