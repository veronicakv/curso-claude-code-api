# Plan: recurso Tareas (v1 y v2) y cierre del `409` de Proyectos

Estado: acordado el plan; sin implementación. Alcance: las secciones **Tareas v1**
y **Tareas v2: Fechas Límite** de `docs/contrato-api.md`, más la rama `409` de
`DELETE /projects/{id}` que quedó diferida en `docs/plan-proyectos.md`.

## Fuentes

`docs/contrato-api.md` (Tareas v1, Tareas v2, Convenciones, Normalización de
texto, Orden de las listas, Esquemas de Respuesta, Matriz Mínima de Tests),
`docs/decisiones-ingenieria.md`, `CLAUDE.md`, `README.md`,
`docs/plan-persistencia.md` y `docs/plan-proyectos.md` (base ya implementada e
integrada en `main`: `states`, `projects`, migraciones, `app/db.py`, `app/text.py`).

## Fuera de alcance

- Recordatorios, scheduler, zona horaria preferida del usuario y cambio
  automático de estado (el propio contrato los excluye en Tareas v2).
- Paginación o metadatos de colección: el contrato exige lista JSON en la raíz.
- Borrado en cascada de tareas al borrar un proyecto: el contrato lo prohíbe
  (`409`, no cascada).
- Endpoints o filtros de tareas no listados en el contrato (p. ej. filtrar por
  `title`, por rango de `due_at`, ordenar por otro campo).
- `docs/glosario.md`, CI, hooks, `Makefile`, autenticación.
- Cambiar el esquema de respuesta de Proyectos o Estados.

## Archivos que no se tocan

`docs/contrato-api.md`, `docs/decisiones-ingenieria.md`, `CLAUDE.md`,
`docs/plan-persistencia.md`, `docs/plan-proyectos.md`, `.gitignore`, `.env` (no se
abre). `README.md` solo si un incremento añade un comando nuevo que documentar; no
se prevé.

## Estado inicial del repositorio

- Rama `feature/tasks`, creada desde `main` (`ade5061`). Árbol limpio.
- `app/models.py`: `Base`, `State`, `Project` (`id`, `name` `Text` NOT NULL,
  `description` `Text` NULL). No hay `Task`.
- `app/schemas.py`: `StateOut`, `ProjectIn`, `ProjectOut`, `ProjectPatch`; usa
  `ConfigDict(extra="forbid")` y `from_attributes=True`. No hay esquemas de tarea.
- `app/projects.py`: `APIRouter` con `POST/GET/GET{id}/PATCH/DELETE /projects`.
  `delete_project` hoy hace `204`/`404` sin comprobar tareas.
- `app/text.py`: `normalizar_texto_requerido` (recorte + rechazo por categoría
  Unicode `Cc/Cf/Zl/Zp/Zs`). Reutilizable para `title`.
- `app/main.py`: monta `health`, `states` y el router de proyectos. No hay
  `app/clock.py` ni router de tareas.
- `alembic/versions/`: `453c2e2272d5`, `9f1c7b6a2d34`, `3459cae2a91f`.
  `head` = `3459cae2a91f`. `env.py` toma la URL de `app/db.py`.
- `tests/`: `test_health`, `test_db_config`, `test_migrations`, `test_states`,
  `test_projects`. `pytest -q` en `main` -> 29 passed. Patrón de tests de
  persistencia: base `taskflow_test`, `alembic upgrade head`, override de
  `get_session`, `httpx.ASGITransport`.
- Dependencias en `uv.lock`: `fastapi`, `sqlalchemy`, `psycopg`, `alembic`,
  `pydantic` v2, `pydantic-settings`; dev: `pytest`, `pytest-asyncio`, `httpx`,
  `ruff`. **Este plan no añade dependencias**: `datetime` y `zoneinfo` son stdlib;
  `pydantic` v2 valida `datetime` con zona de fábrica.
- `pyproject.toml`: ruff `line-length = 100`, reglas `E, F, I, UP, B`; pytest
  `asyncio_mode = "auto"`.

## Decisiones acordadas

- **Tabla `tasks`**: `id` PK; `title` `Text` NOT NULL; `description` `Text` NULL;
  `project_id` INTEGER NOT NULL, FK a `projects.id` con `ON DELETE RESTRICT`;
  `state_id` INTEGER NOT NULL, FK a `states.id` con `ON DELETE RESTRICT`;
  `due_at` `TIMESTAMP(timezone=True)` NULL. Modelo `Task` en `app/models.py`.
  Por qué encaja: `projects` y `states` ya existen con `id` entero; `RESTRICT`
  materializa "no hay borrado en cascada implícito" del contrato como red de
  seguridad a nivel BD.
- **Validación de `title`**: se reutiliza `normalizar_texto_requerido` de
  `app/text.py` (recorte + `422` si no deja carácter visible, por categoría
  Unicode). Es la regla que el contrato fija **explícitamente** para `title`.
- **Validación de referencias**: `POST /tasks` y `PATCH /tasks/{id}` comprueban
  que `project_id` y `state_id` existan; si no, `404` con `{"detail": ...}`. No se
  crean implícitamente (Convenciones del contrato).
- **`due_at` — almacenamiento y serialización**: la entrada debe traer zona; se
  normaliza a UTC al guardar (`TIMESTAMP` con tz). En las respuestas se serializa
  **siempre** como `...Z`, sin desplazamiento `+00:00` y sin microsegundos
  (`2026-03-01T09:00:00Z`), vía un serializador de campo en el esquema de salida.
  Por qué encaja: lo exige "Esquemas de Respuesta"; `pydantic` v2 permite un
  `field_serializer` sin dependencias nuevas.
- **`due_at` sin zona -> `422`**: una fecha entrante sin offset se rechaza. En
  `PATCH`, `due_at: null` borra la fecha; `due_at` ausente no la toca. Omitir
  `due_at` en `POST` conserva compatibilidad v1 (`due_at` -> `null` en la salida).
- **`PATCH /tasks/{id}`**: actualización parcial. Campo ausente no cambia;
  `title` presente se renormaliza; `project_id`/`state_id` presentes se
  revalidan (existencia -> `404`); `due_at` presente se revalida (zona -> `422`,
  `null` permitido); cuerpo `{}` -> `200` sin cambios; `extra="forbid"` -> clave
  desconocida `422`. Estado inexistente al cambiar `state_id` -> `404`.
- **`GET /tasks` — filtros**: `project_id` y `state_id` como query params
  opcionales, enteros, combinables (AND). Un valor no entero -> `422`. Filtrar por
  un `project_id`/`state_id` inexistente devuelve lista vacía (`200`), no `404`:
  el filtro no es una referencia que se cree ni se exija que exista.
- **`GET /tasks?overdue=true`**: `overdue` solo acepta `true`; `false` o
  cualquier otro valor -> `422`. `true` devuelve tareas con `due_at` **anterior al
  instante de evaluación** y `state_id` distinto del de `HECHA`. Una tarea sin
  `due_at` nunca está vencida. Combinable con `project_id`/`state_id`.
- **Instante de evaluación**: lo da `app/clock.py::now_utc() -> datetime`
  (`datetime.now(UTC)`), inyectable en tests vía `app.dependency_overrides` o
  sustitución directa, para fijar "ahora" y probar el borde exacto de corte.
  Por qué encaja: sin dependencia nueva; el resto de la app ya usa el patrón de
  dependencias de FastAPI (`get_session`).
- **Orden de `GET /tasks`**: por `id` ascendente, también con filtros aplicados
  (Orden de las listas).
- **Esquema de respuesta de tarea**: exactamente `id`, `title`, `description`,
  `project_id`, `state_id`, `due_at` (v2). `description` y `due_at` ausentes se
  devuelven como `null`, no se omiten. `extra="forbid"` en el esquema de salida.
- **Cierre del `409` de Proyectos**: `delete_project` consulta si existe alguna
  fila en `tasks` con ese `project_id`; si la hay, `409` con `{"detail": ...}`
  antes de intentar el borrado. La FK `ON DELETE RESTRICT` queda como red de
  seguridad. Se actualiza el docstring de `app/projects.py`; el contrato no se
  toca (este plan cubre la incógnita que dejó abierta el plan de Proyectos).
- **Migración v2**: `due_at` entra en la **misma** migración que crea `tasks`
  (no hay datos v1 previos que preservar). El "rollback de v2" de la Matriz
  Mínima se satisface con el `downgrade` de esa migración, que elimina `tasks`.
- **Pruebas contra PostgreSQL real**: nuevo `tests/test_tasks.py` con el patrón
  de `test_projects.py`. Si PostgreSQL no está accesible, fallan; no se hace skip.
- **Un incremento = un commit que se confirma solo**. Al terminar cada
  incremento se para y se espera aprobación; no se encadena el siguiente.

## Incrementos

### Incremento 1 — Migración y modelo de `tasks` (v1 + `due_at`)

- **Qué:** nueva revisión de Alembic (`down_revision = "3459cae2a91f"`) que crea
  `tasks` (`id` PK; `title` `Text` NOT NULL; `description` `Text` NULL;
  `project_id` INT NOT NULL FK->`projects.id` `ON DELETE RESTRICT`; `state_id`
  INT NOT NULL FK->`states.id` `ON DELETE RESTRICT`; `due_at` `TIMESTAMP(tz)`
  NULL), con `upgrade`/`downgrade`. Modelo `Task` en `app/models.py`. Sin rutas
  ni esquemas.
- **Comprobación:**
  - Test que falla primero: `tests/test_migrations.py::test_upgrade_crea_tasks_y_downgrade_la_elimina`
    — tras `alembic upgrade head` existe `tasks` con las 6 columnas y las dos FK
    con `RESTRICT`; `alembic downgrade -1` la elimina y deja `projects`, `states`
    y el catálogo intactos.
  - `alembic upgrade head` dos veces seguidas no falla.
  - `alembic downgrade base` + `upgrade head` reconstruye todo sin error
    (cubre el "rollback de v2" de la Matriz Mínima).
  - `uv run ruff check .` limpio; `uv run pytest -q` verde (salud, estados,
    proyectos intactos).
  - Ampliar la limpieza de fixtures de `test_migrations`/`test_states`/
    `test_projects` para soltar también `tasks` entre corridas.

### Incremento 2 — `POST /tasks` y `GET /tasks/{id}`

- **Qué:** `app/tasks.py` con `APIRouter`, montado en `app/main.py`. En
  `app/schemas.py`: `TaskIn` (`title` normalizado, `description` opcional,
  `project_id`/`state_id` obligatorios, `due_at` opcional con zona, `extra="forbid"`)
  y `TaskOut` (los 6 campos exactos; `field_serializer` de `due_at` a `...Z` sin
  microsegundos; `from_attributes=True`, `extra="forbid"`). `POST /tasks` -> `201`
  validando `title`, existencia de `project_id` y `state_id` (-> `404`), y zona de
  `due_at` (-> `422`). `GET /tasks/{id}` -> `200` con esquema exacto o `404`.
- **Comprobación:**
  - Test que falla primero: `tests/test_tasks.py::test_post_crea_y_get_por_id`
    — crea proyecto y usa un `state_id` del catálogo; `POST /tasks` con `title`,
    `project_id`, `state_id` -> `201` y cuerpo con exactamente
    `{id, title, description, project_id, state_id, due_at}`, `description` y
    `due_at` `null`; `GET /tasks/{id}` -> `200` con el mismo esquema.
  - Test: `POST /tasks` con `project_id` inexistente -> `404` con `detail`; con
    `state_id` inexistente -> `404` con `detail`.
  - Test: `title` vacío tras recortar y `title` solo invisibles (`U+200B`) ->
    `422` con `detail`.
  - Test: `due_at` con zona -> se guarda y se devuelve como `...Z` sin
    microsegundos; `due_at` **sin** zona -> `422`.
  - Test: clave desconocida en el cuerpo -> `422`. `GET /tasks/{id}` inexistente
    -> `404`; `id` no entero -> `422`.
  - `uv run ruff check .` limpio; `uv run pytest -q` verde.

### Incremento 3 — `GET /tasks` con filtros `project_id` y `state_id`

- **Qué:** `GET /tasks` -> `200`, lista JSON en la raíz, orden por `id`
  ascendente. Query params opcionales `project_id` y `state_id` (enteros),
  solos o combinados (AND). Sin `overdue` todavía.
- **Comprobación:**
  - Test que falla primero: `tests/test_tasks.py::test_get_tasks_filtros_solos_y_combinados`
    — con tareas en 2 proyectos y 2 estados: sin filtro devuelve todas en orden
    por `id`; `?project_id=` filtra; `?state_id=` filtra; ambos combinados
    aplican AND.
  - Test: dos llamadas idénticas (con y sin filtro) devuelven los `id` en la
    misma posición.
  - Test: `?project_id=` de un proyecto sin tareas -> `200` con lista vacía;
    `?project_id=abc` -> `422`.
  - Test: el cuerpo es una lista en la raíz, no un objeto envolvente.
  - `uv run ruff check .` limpio; `uv run pytest -q` verde.

### Incremento 4 — `PATCH /tasks/{id}` y `DELETE /tasks/{id}`

- **Qué:** `TaskPatch` en `app/schemas.py` (todos los campos opcionales,
  `extra="forbid"`). `PATCH /tasks/{id}` -> `200` con actualización parcial
  consistente: `title` presente renormalizado; `project_id`/`state_id` presentes
  revalidados (-> `404` si no existen); `due_at` presente revalidado (zona ->
  `422`, `null` permitido); campo ausente no cambia; cuerpo `{}` -> `200` sin
  cambios; `404` si la tarea no existe. `DELETE /tasks/{id}` -> `204` sin cuerpo,
  o `404` si no existe.
- **Comprobación:**
  - Test que falla primero: `tests/test_tasks.py::test_patch_parcial_consistente`
    — cambiar solo `description` no toca el resto; cambiar `state_id` a otro
    válido persiste; `PATCH {}` -> `200` sin cambios; `PATCH` con `project_id`
    inexistente -> `404`; `PATCH` con `due_at` sin zona -> `422`; `due_at: null`
    borra la fecha.
  - Test: `PATCH`/`DELETE` sobre `id` inexistente -> `404` con `detail`.
  - Test: `DELETE /tasks/{id}` existente -> `204` sin cuerpo; `GET` posterior ->
    `404`.
  - Test: clave desconocida en el cuerpo de `PATCH` -> `422`.
  - `uv run ruff check .` limpio; `uv run pytest -q` verde.

### Incremento 5 — `GET /tasks?overdue=true` y `app/clock.py`

- **Qué:** `app/clock.py::now_utc()`. `GET /tasks` acepta `overdue`; solo `true`
  es válido (`false`/otro -> `422`). `?overdue=true` filtra tareas con `due_at`
  anterior a `now_utc()` y `state_id` distinto del de `HECHA`; una tarea sin
  `due_at` no está vencida. Combinable con `project_id`/`state_id`.
- **Comprobación:**
  - Test que falla primero: `tests/test_tasks.py::test_overdue_true`
    — con `now_utc` fijado en los tests: tarea con `due_at` pasado y estado no
    `HECHA` aparece; con `due_at` futuro no aparece; con `due_at` pasado pero
    estado `HECHA` no aparece; sin `due_at` no aparece.
  - Test: borde exacto — `due_at` == `now_utc()` no cuenta como vencida
    (estrictamente anterior).
  - Test: `?overdue=false` -> `422`; `?overdue=1` -> `422`.
  - Test: `?overdue=true&project_id=` combina AND.
  - `uv run ruff check .` limpio; `uv run pytest -q` verde.

### Incremento 6 — Cierre del `409` de `DELETE /projects/{id}`

- **Qué:** en `app/projects.py`, `delete_project` consulta si existe alguna tarea
  con ese `project_id`; si la hay -> `409` con `{"detail": ...}` sin borrar; si no
  -> `204` como hasta ahora; `404` si el proyecto no existe. Se actualiza el
  docstring del módulo.
- **Comprobación:**
  - Test que falla primero: `tests/test_projects.py::test_delete_proyecto_con_tareas_es_409`
    — crear proyecto + tarea en él; `DELETE /projects/{id}` -> `409` con `detail`;
    el proyecto y la tarea siguen existiendo. Borrar antes la tarea y luego el
    proyecto -> `204`.
  - Test: los casos previos de `DELETE /projects` (`204` sin tareas, `404`
    inexistente) siguen verdes.
  - `uv run ruff check .` limpio; `uv run pytest -q` verde.

## Incógnitas para planes posteriores

- Ninguna dentro del alcance de Tareas v1+v2. Recordatorios, scheduler, zona
  preferida y cambio automático de estado quedan fuera por decisión del contrato.
- Mensaje exacto de `detail` en `404`/`409`/`422`: el contrato solo fija la clave
  de primer nivel; el texto se concreta al implementar cada incremento.
