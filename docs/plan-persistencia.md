# Plan: conexión de la API a PostgreSQL

Estado: acordado el plan; sin implementación. Alcance de este plan: solo las
secciones **Salud** y **Estados** del contrato.

Fuentes: `docs/contrato-api.md` (Salud, Estados), `docs/decisiones-ingenieria.md`,
`CLAUDE.md`.

## Fuera de alcance

Proyectos, tareas, filtros, `due_at`, skills, hooks y CI.

## Archivos que no se tocan

`docs/contrato-api.md`, `docs/decisiones-ingenieria.md`, `CLAUDE.md`,
`.gitignore`, `.env`. No se abre `.env`.

## Reglas de trabajo

- Cada incremento es un commit que se confirma solo. Al terminar uno, se para y
  se espera aprobación; no se encadena el siguiente.
- Una capacidad nueva empieza por un test que falla por la ausencia de esa
  capacidad.
- No se debilita ni elimina una comprobación para conseguir verde.
- Las pruebas de persistencia corren contra PostgreSQL real, nunca SQLite.
- El esquema cambia por migraciones de Alembic con `upgrade` y `downgrade`,
  probadas en ambos sentidos. El seed de estados es idempotente.

## Estado inicial del repositorio

- `app/main.py`: solo `GET /health` -> `200 {"status": "ok"}`. Sin capa de datos.
- `tests/test_health.py`: único test, asíncrono, vía `httpx.ASGITransport`.
- Dependencias: `fastapi`, `uvicorn`; dev: `pytest`, `pytest-asyncio`, `httpx`,
  `ruff`. No hay `alembic`, `sqlalchemy`, `psycopg`/`asyncpg` ni
  `pydantic-settings` (confirmado en `uv.lock`).
- `compose.yaml`: servicio `db` con `postgres:18-alpine`, healthcheck
  `pg_isready`, volumen `pgdata`, puerto `${POSTGRES_PORT:-5432}`.
- `.env.example`: `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`,
  `POSTGRES_PORT`.
- No hay `alembic.ini` ni carpeta de migraciones. No hay `docs/glosario.md`
  (el contrato lo enlaza pero no existe). No hay CI ni `Makefile`.
- Rama `feature/persistencia`, sin diferencias respecto a `main`.
- `docs/decisiones-ingenieria.md` fija **Alembic** como motor de migraciones.

## Decisiones acordadas

- Capa de acceso a datos: SQLAlchemy 2.x ORM.
- Driver de PostgreSQL: `psycopg` v3.
- Lectura de configuración: `pydantic-settings`. Decisión tomada: se adopta, sin
  condicional; el Incremento 1 lo instala como dependencia fija.
  Por qué encaja: `fastapi` ya arrastra `pydantic` v2 (2.13.5 en `uv.lock`), así
  que `pydantic-settings` reutiliza esa familia en lugar de sumar una nueva.
- Módulo de configuración de conexión: `app/db.py`. Decisión tomada entre las dos
  opciones que barajaba el plan (`app/config.py` o `app/db.py`).
  Por qué encaja: el paquete `app/` ya existe con `__init__.py` y hoy solo tiene
  `main.py`; `app/db.py` concentra la URL de conexión y, más adelante, el engine
  y la sesión de SQLAlchemy en un único punto de la capa de datos.
- Idempotencia del seed de estados: `INSERT ... ON CONFLICT DO NOTHING` sobre una
  restricción única de `code`. Decisión tomada entre `ON CONFLICT DO NOTHING` y
  un "equivalente por `code`" que el plan dejaba sin concretar.
  Por qué encaja: la migración corre contra `postgres:18-alpine` (`compose.yaml`)
  y los tests contra PostgreSQL real, nunca SQLite, así que `ON CONFLICT` de
  PostgreSQL está disponible y no hace falta emularlo.
- Tests de persistencia: PostgreSQL real usando la instancia de `compose.yaml`,
  con una base de datos dedicada para tests. Si PostgreSQL no está accesible,
  los tests que lo requieren **fallan**; no se hace skip para conseguir verde.
- `README.md` se puede modificar para documentar el comando de migración.

## Incrementos

### Incremento 1 — Dependencias y configuración de conexión

- **Qué:** añadir a `pyproject.toml` driver + capa de datos + Alembic +
  `pydantic-settings`; `uv lock`; módulo `app/db.py` que arme la URL de conexión
  desde las variables `POSTGRES_*`. Sin migraciones ni endpoints todavía.
- **Comprobación:**
  - `uv sync --locked` instala sin error.
  - `uv run ruff check .` limpio.
  - `uv run pytest -q` sigue verde (solo `test_health`).
  - Test nuevo que falla primero: importa el módulo de config y afirma que
    construye una URL `postgresql+psycopg://...` a partir del entorno.

### Incremento 2 — Alembic operativo con una migración base

- **Qué:** `alembic init`; ajustar `env.py` para tomar la URL de `app/db.py`
  (no de `alembic.ini`); primera revisión con `upgrade`/`downgrade`
  (creación de la tabla `states` vacía, sin datos).
- **Comprobación:**
  - Test que falla primero: `alembic upgrade head` crea la tabla `states`;
    `alembic downgrade base` la elimina.
  - `alembic upgrade head` dos veces seguidas no falla.
  - `ruff` limpio, `pytest -q` verde.

### Incremento 3 — Seed idempotente del catálogo de estados

- **Qué:** nueva revisión de Alembic que inserta `PENDIENTE`, `EN_CURSO`,
  `BLOQUEADA`, `HECHA` con su campo de orden, de forma idempotente con
  `INSERT ... ON CONFLICT DO NOTHING` sobre la restricción única de `code`.
- **Comprobación:**
  - Test que falla primero: tras `upgrade head`, la tabla contiene exactamente
    los 4 `code` esperados en el orden del catálogo.
  - Test: correr la migración de seed dos veces deja 4 filas, no 8.
  - Test: `downgrade` de esta revisión vacía la tabla; `upgrade` la repuebla.
  - `ruff` limpio, `pytest -q` verde.

### Incremento 4 — Endpoint `GET /states`

- **Qué:** ruta que lee la tabla y devuelve la lista con el esquema exacto
  `{"id", "code"}`, ordenada por campo de orden con `id` como desempate.
- **Comprobación:**
  - Test que falla primero: `GET /states` -> `200`, cuerpo es una lista JSON en
    la raíz con 4 elementos, cada uno con exactamente las claves `id` y `code`,
    en el orden del catálogo.
  - Test: dos llamadas idénticas devuelven los `id` en la misma posición.
  - Test: no hay `POST`/`DELETE` de estados.
  - `ruff` limpio, `pytest -q` verde, `test_health` intacto.
