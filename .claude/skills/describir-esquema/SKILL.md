---
name: describir-esquema
description: >-
  Redacta docs/esquema.md a partir del estado real de app/models.py y de
  alembic/versions/ en el momento de invocarla: un diagrama de tablas y
  relaciones en texto versionable, y un diccionario de datos con una fila por
  columna. Analiza las migraciones en orden y las contrasta con los modelos.
  DESCRIBE, no modifica: no toca modelos, migraciones, docs/contrato-api.md ni
  la base de datos; su única salida es docs/esquema.md. Úsala cuando quieras
  documentar el esquema de la base o actualizar esa documentación tras un
  cambio de migraciones.
---

# Describir el esquema de la base

Esta skill produce **un solo archivo, `docs/esquema.md`**. No modifica
`app/models.py`, ni nada bajo `alembic/`, ni `docs/contrato-api.md`, ni ningún
otro archivo del repo, ni se conecta a PostgreSQL ni ejecuta migraciones. Si al
describir el esquema detectas que una migración o un modelo está mal, **no lo
arregles**: anótalo como discrepancia en `docs/esquema.md` y díselo al usuario.

## 1. Estado real del que se parte

Antes de escribir nada, léelo del repositorio tal como está ahora, no de lo que
otra documentación diga que existe:

- **Todos los archivos de `alembic/versions/*.py`.** Ordénalos siguiendo la
  cadena `down_revision → revision` (no por nombre de archivo ni por fecha):
  localiza la raíz (`down_revision = None`) y encadena hasta el head. Ese es el
  orden en que se aplican y el orden en que hay que leerlas.
- **`app/models.py`** (y cualquier otro módulo con modelos ORM que importe
  `Base`, si el paquete `app/` los tuviera).
- Para cada migración, mira qué hace realmente: `create_table`, `add_column`,
  `drop_column`, `create_check_constraint`, `ForeignKeyConstraint`,
  `UniqueConstraint`, `create_index`, `op.execute(...)` de seed. Fíjate en
  `nullable`, `server_default`, tipos concretos (`Text` vs `String(n)`,
  `DateTime(timezone=True)`), nombres de constraints y `ondelete`.

## 2. Cómo se construye la verdad del esquema

- **Las migraciones son el historial real.** El esquema vigente es el resultado
  de aplicar `upgrade()` de la raíz al head, en orden: una columna añadida por
  una migración posterior cuenta igual que una creada en el `create_table`
  inicial. Recórrelas acumulando el estado tabla por tabla.
- **Los modelos son el contraste, no la fuente.** Compara el estado acumulado de
  las migraciones con lo declarado en `app/models.py`. Si coinciden, descríbelo
  una vez. Si **no** coinciden (una columna en el modelo que ninguna migración
  crea, un tipo distinto, un `nullable` distinto, una constraint que el modelo
  no refleja), gana la migración como descripción del esquema y **añade una
  nota de discrepancia** en `docs/esquema.md` diciendo qué dice cada lado.
- **No inventes.** No añadas una columna, relación, índice o restricción que no
  esté explícita en una migración. Si algo no está (p. ej. no hay
  `create_index` para una FK), no lo supongas: puedes señalar la ausencia si es
  relevante, pero no la conviertas en un hecho afirmado.

## 3. Qué contiene `docs/esquema.md`

Un encabezado corto que diga qué es el archivo y que se regenera con esta skill
(`/describir-esquema`), y que la fuente es `alembic/versions/` contrastado con
`app/models.py`. Luego dos partes:

### Parte 1 — Diagrama de tablas y relaciones

En **texto versionable y renderizable dentro del repositorio**: un bloque
` ```mermaid ` con un `erDiagram` (entidad-relación). Nada de imágenes, nada de
enlaces a servicios externos, nada de PNG/SVG adjunto.

- Una entidad por tabla real.
- Dentro de cada entidad, sus columnas con tipo y marca de clave (`PK`, `FK`)
  cuando aplique.
- Una arista por cada `ForeignKeyConstraint` real, etiquetada con la relación
  y anotada con su `ondelete` (p. ej. `RESTRICT`) en el texto que acompaña al
  diagrama, no inventando cardinalidades que las migraciones no fijen.

Si el `erDiagram` no basta para mostrar algo (constraints con nombre, un
`CHECK`), va como lista breve **debajo** del bloque, no dentro.

### Parte 2 — Diccionario de datos

Una tabla Markdown por cada tabla de la base. **Una fila por columna real**,
con estas columnas:

| Columna | Significado |
|---|---|
| `nombre` | nombre exacto de la columna |
| `tipo` | el tipo tal como lo crea la migración (`INTEGER`, `TEXT`, `VARCHAR(32)`, `TIMESTAMP WITH TIME ZONE`, …) |
| `¿nulos?` | `NOT NULL` o `NULL`, según la migración |
| `significado` | solo cuando **no** sea evidente por el nombre: qué representa, rango, unidad, de dónde sale su valor, qué migración la añadió si fue posterior al `create_table` |

Debe cubrir **todas** las columnas creadas por las migraciones, incluidas las
que añadieron migraciones posteriores (p. ej. una `add_column` de v2). Si una
columna ya está explicada en `docs/contrato-api.md`, **no repitas la
explicación**: enlaza a la sección correspondiente de ese documento y limita la
fila a nombre/tipo/nulos.

## 4. No dupliques el contrato

`docs/contrato-api.md` es la fuente del comportamiento observable (normalización
de `title`, reglas de `due_at`, valores del catálogo de estados, orden de las
colecciones, semántica de `priority`). `docs/esquema.md` describe **la
estructura física**: tablas, columnas, tipos, nulabilidad, FKs, constraints con
nombre, y el historial de migraciones. Cuando un punto ya viva en el contrato,
enlázalo (`[..](contrato-api.md#seccion)`) en vez de copiarlo. No copies tampoco
reglas de `CLAUDE.md` ni de `.claude/rules/`.

## 5. Cómo entregar

1. Lee `alembic/versions/*.py` y ordénalas por la cadena de revisiones.
2. Lee `app/models.py`.
3. Acumula el estado del esquema recorriendo los `upgrade()` en orden.
4. Contrasta con los modelos; anota discrepancias.
5. Escribe `docs/esquema.md` con las dos partes de la sección 3.
6. Muestra al usuario la ruta y un resumen: cuántas tablas, cuántas columnas y
   qué discrepancias (si las hay).

La skill no modifica ningún archivo salvo `docs/esquema.md`.
