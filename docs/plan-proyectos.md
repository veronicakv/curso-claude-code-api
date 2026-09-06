# Plan: recurso Proyectos

Estado: acordado el plan; sin implementación. Alcance de este plan: la sección
**Proyectos** del contrato, incluido `DELETE /projects/{id}` en su forma básica
(`204` al borrar, `404` si no existe). La rama `409` por proyecto con tareas
queda diferida al incremento de Tasks: hoy no existen la tabla `tasks` ni la
relación `tasks.project_id`.

## Fuentes

`docs/contrato-api.md` (Proyectos, Convenciones, Normalización de texto, Orden de
las listas, Esquemas de Respuesta, Matriz Mínima de Tests),
`docs/decisiones-ingenieria.md`, `CLAUDE.md`, `README.md`,
`docs/plan-persistencia.md` (base ya implementada: `states`, migraciones,
`app/db.py`).

## Fuera de alcance

- La rama `409` de `DELETE /projects/{id}` (borrar un proyecto que tiene tareas)
  y la FK `tasks.project_id`: no se crea ninguna referencia a `tasks` en este
  plan; esa rama se implementa en el incremento de Tasks. El `DELETE` básico
  (`204`/`404`) sí entra en este plan, en el Incremento 4.
- Tareas (tabla, endpoints, filtros), `due_at`, `overdue`.
- Normalización de `title` de tarea y el trabajo de invisibles Unicode de la
  sesión 7. Este plan solo trae esa regla al `name` de proyecto (ver Decisiones).
- Paginación o metadatos de colección: el contrato exige lista JSON en la raíz.
- `docs/glosario.md`, CI, hooks, `Makefile`, autenticación, timestamps,
  borrado en cascada.

## Archivos que no se tocan

`docs/contrato-api.md`, `docs/decisiones-ingenieria.md`, `CLAUDE.md`,
`.gitignore`, `.env` (no se abre). `README.md` solo se toca si un incremento
añade un comando nuevo que documentar; no se prevé.

## Estado inicial del repositorio

- Rama `feature/projects`. Único commit por delante de `main`: la skill
  `planificar-incremento`. Sin cambios sin confirmar.
- `app/main.py`: `GET /health` y `GET /states` (este último con sesión de BD).
  No hay `APIRouter`; las dos rutas están directamente en `main.py`.
- `app/models.py`: `Base` declarativa y modelo `State` (`id`, `code` único
  `String(32)`, `sort_order`). No hay modelo `Project`.
- `app/schemas.py`: `StateOut` con `ConfigDict(from_attributes=True,
  extra="forbid")`. No hay esquemas de proyecto.
- `app/db.py`: engine perezoso, `get_session` como dependencia, `DATABASE_URL`
  con prioridad sobre `POSTGRES_*`.
- `alembic/versions/`: `453c2e2272d5` (crea `states`) y `9f1c7b6a2d34` (seed
  idempotente). `head` = `9f1c7b6a2d34`. `env.py` toma la URL de `app/db.py`.
- `tests/`: `test_health.py`, `test_db_config.py`, `test_migrations.py`,
  `test_states.py`. Los de persistencia corren contra PostgreSQL real
  (`taskflow_test`), nunca SQLite, y fallan si la BD no está accesible.
- Dependencias en `uv.lock`: `fastapi`, `sqlalchemy`, `psycopg`, `alembic`,
  `pydantic` v2 (2.13.5), `pydantic-settings`. Dev: `pytest`, `pytest-asyncio`,
  `httpx`, `ruff`. Este plan no añade ninguna dependencia.
- `pyproject.toml`: ruff `line-length = 100`, reglas `E, F, I, UP, B`;
  pytest `asyncio_mode = "auto"`.

## Decisiones acordadas

- **Validación de `name`**: la misma normalización que el contrato fija para
  `title` de tarea. Se recortan los extremos antes de validar y guardar, y se
  rechaza con `422` el valor que no deja ningún carácter visible, comprobando por
  categoría Unicode y rechazando `Cc`, `Cf`, `Zl`, `Zp`, `Zs`.
  Por qué encaja: el contrato ya especifica esa regla al detalle; aplicar otra
  distinta a `name` dejaría dos comportamientos de texto divergentes en la misma
  API.
- **Helper compartido `app/text.py`**: una función `normalizar_texto_requerido`
  que hace recorte + comprobación de visibles y levanta el error de validación.
  La usa el esquema de entrada de proyecto y, más adelante, el de tarea.
  Por qué encaja: `pydantic` v2 ya está en `uv.lock`; centralizar la regla evita
  que la sesión 7, que trabaja este defecto a fondo, tenga que corregir dos
  implementaciones.
- **Módulo `app/projects.py` con `APIRouter`**, montado en `app/main.py` con
  `app.include_router`. Las rutas de proyecto no se escriben en `main.py`.
  Por qué encaja: `models.py` y `schemas.py` ya separan por responsabilidad;
  `main.py` hoy sostiene `health` y `states`, y sumarle un CRUD lo vuelve
  ilegible.
- **Tipos de columna**: `name` y `description` como `Text`, `name` `NOT NULL`,
  `description` `NULL`. Sin límite de longitud ni validación de longitud.
  Por qué encaja: `code` es un token de catálogo acotado (`String(32)`); `name` y
  `description` son texto libre y el contrato no fija ningún máximo, así que el
  plan no inventa un `422` por longitud que el contrato no pide.
- **Cuerpo de las peticiones con `extra="forbid"`**: `POST` y `PATCH` rechazan
  con `422` una clave desconocida en el cuerpo.
  Por qué encaja: `app/schemas.py` ya usa `extra="forbid"` como estilo de la
  casa, y el contrato insiste en "ni más ni menos" para los campos.
- **Semántica de `PATCH`**: actualización parcial. Un campo ausente no cambia;
  `name` presente se revalida con la regla de arriba; `description` se puede
  fijar a `null` explícitamente. Cuerpo `{}` responde `200` con el recurso sin
  cambios. Proyecto inexistente: `404` con `{"detail": "<mensaje>"}`.
  Por qué encaja: `pydantic` v2 distingue campo ausente de `null` con
  `model_fields_set`, sin dependencias nuevas; no se inventa un `422` para el
  cuerpo vacío.
- **Orden de `GET /projects`**: por `id` ascendente, como fija el contrato.
- **Pruebas contra PostgreSQL real**: nuevos tests en `tests/test_projects.py`
  reutilizando el patrón de `test_states.py` (base `taskflow_test`, `alembic
  upgrade head`, override de `get_session`). Si PostgreSQL no está accesible,
  fallan; no se hace skip.
- **`DELETE /projects/{id}` básico ahora**: `204` sin cuerpo al borrar un
  proyecto existente y `404` con `detail` si el `id` no existe. La rama `409`
  (proyecto con tareas) se difiere.
  Por qué encaja: el contrato ya fija `DELETE` `204`/`409`, y el `204` es la
  rama correcta mientras ninguna fila pueda tener tareas; el `409` es
  inalcanzable e intesteable sin la tabla `tasks`, así que se separa el borrado
  básico del comportamiento dependiente de Tasks.
- **Un incremento = un commit que se confirma solo**. Al terminar cada
  incremento se para y se espera aprobación; no se encadena el siguiente.

## Incrementos

### Incremento 1 — Migración y modelo de `projects`

- **Qué:** nueva revisión de Alembic con `down_revision = "9f1c7b6a2d34"` que crea
  la tabla `projects` (`id` PK, `name` `Text` `NOT NULL`, `description` `Text`
  `NULL`), con `upgrade` y `downgrade`. Modelo `Project` en `app/models.py`. Sin
  rutas ni esquemas todavía.
- **Comprobación:**
  - Test que falla primero: `tests/test_migrations.py::test_upgrade_crea_projects_y_downgrade_la_elimina`
    — tras `alembic upgrade head` existe la tabla `projects` con las columnas
    `id`, `name`, `description`; `alembic downgrade -1` la elimina y deja `states`
    y su catálogo intactos.
  - `uv run alembic upgrade head` dos veces seguidas no falla.
  - `uv run alembic downgrade base` seguido de `uv run alembic upgrade head`
    reconstruye todo sin error.
  - `uv run ruff check .` limpio.
  - `uv run pytest -q` verde, con los tests de salud y estados intactos.

### Incremento 2 — `POST /projects`, `GET /projects` y `GET /projects/{id}`

- **Qué:** `app/text.py` con `normalizar_texto_requerido`. En `app/schemas.py`:
  `ProjectIn` (`name` obligatorio y normalizado, `description` opcional,
  `extra="forbid"`) y `ProjectOut` (`id`, `name`, `description`;
  `from_attributes=True`, `extra="forbid"`; `description` ausente se serializa
  como `null`). `app/projects.py` con `APIRouter`: `POST` → `201` con el recurso
  creado; `GET /projects` → `200` con lista JSON en la raíz ordenada por `id`
  ascendente; `GET /projects/{id}` → `200` con el esquema exacto, o `404` con
  `{"detail": "<mensaje>"}` si no existe. Router montado en `app/main.py`.
- **Comprobación:**
  - Test que falla primero: `tests/test_projects.py::test_post_crea_y_get_lista_en_orden`
    — `POST {"name": "Casa"}` → `201` y cuerpo con exactamente las claves `id`
    (entero positivo), `name` (`"Casa"`) y `description` (`null`); tras tres
    altas, `GET /projects` → `200`, lista de 3 elementos ordenada por `id`
    ascendente.
  - Test: `GET /projects` devuelve una lista en la raíz, no un objeto envolvente
    con metadatos.
  - Test: `GET /projects/{id}` de un proyecto existente → `200` con exactamente
    las claves `id`, `name`, `description`.
  - Test: `GET /projects/{id}` con un `id` inexistente → `404` con la clave de
    primer nivel `detail`.
  - Test: `GET /projects/{id}` con un `id` no entero → `422`.
  - Test: `POST` con `name` que queda vacío tras recortar, y `POST` con `name`
    formado solo por caracteres invisibles (`U+200B`), devuelven `422` con la
    clave de primer nivel `detail`.
  - Test: `POST` con una clave desconocida en el cuerpo → `422`.
  - Test: `POST` sin `name` → `422`.
  - `uv run ruff check .` limpio.
  - `uv run pytest -q` verde; `test_health` y `test_states` intactos.

### Incremento 3 — `PATCH /projects/{id}`

- **Qué:** en `app/projects.py`, `PATCH /projects/{id}` → `200` con actualización
  parcial (campo ausente no cambia; `name` presente se revalida con la
  normalización adoptada en «Decisiones acordadas»; `description` fijable a
  `null`; cuerpo `{}` devuelve el recurso sin cambios), o `404` si no existe.
  Esquema `ProjectPatch` en `app/schemas.py` con todos los campos opcionales y
  `extra="forbid"`.
- **Comprobación:**
  - Test que falla primero: `tests/test_projects.py::test_patch_parcial`
    — crear un proyecto; `PATCH {"description": "x"}` → `200` con `name` sin
    cambios y `description` = `"x"`; `PATCH {"description": null}` → `200` con
    `description` = `null`; `PATCH {}` → `200` sin cambios.
  - Test: `PATCH {"name": "Otro"}` → `200`, y tanto el cuerpo como un
    `GET /projects/{id}` posterior devuelven `name` = `"Otro"`. Es cobertura de
    disciplina del proyecto ("CRUD feliz de proyectos"), no una exigencia
    adicional del contrato.
  - Test: `PATCH` con `name` que no deja carácter visible → `422` con `detail`.
  - Test: `PATCH` sobre un `id` inexistente → `404` con `detail`.
  - Test: `PATCH` con clave desconocida en el cuerpo → `422`.
  - `uv run ruff check .` limpio.
  - `uv run pytest -q` verde; salud, estados y el Incremento 2 intactos.

### Incremento 4 — `DELETE /projects/{id}` básico (`204`/`404`)

- **Qué:** en `app/projects.py`, ruta `DELETE /projects/{project_id}` que borra
  el proyecto y responde `204` sin cuerpo si existe, o `404` con
  `{"detail": "<mensaje>"}` si no existe. Hoy ninguna fila puede tener tareas
  (no existe la tabla `tasks`), así que el borrado siempre cae en la rama `204`.
  No se implementa la rama `409` ni se añade la FK `tasks.project_id`.
- **Comprobación:**
  - Test que falla primero: `tests/test_projects.py::test_delete_borra_y_404_si_no_existe`
    — crear un proyecto; `DELETE /projects/{id}` → `204` sin cuerpo; `GET
    /projects/{id}` posterior → `404`. `DELETE /projects/{id}` sobre un `id`
    inexistente → `404` con la clave de primer nivel `detail`.
  - Test: `DELETE /projects/{id}` con un `id` no entero → `422`.
  - `uv run ruff check .` limpio.
  - `uv run pytest -q` verde; salud, estados y los Incrementos 2 y 3 intactos.

## Incógnitas para planes posteriores

- Rama `409` de `DELETE /projects/{id}`: el incremento de Tasks debe definir
  cómo se detecta que un proyecto "tiene tareas" (consulta previa o restricción
  de FK con captura del error) para devolver `409` en vez del `204`. El `DELETE`
  básico (`204`/`404`) ya queda cubierto por el Incremento 4.
- Mensaje exacto de `detail` en los `404` y `422`: el contrato solo exige que la
  clave de primer nivel sea `detail` y el mensaje sea legible. Se concreta al
  implementar cada incremento, no se decide aquí.
