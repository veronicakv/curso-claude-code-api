# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Qué es este repositorio

TaskFlow API: proyecto de curso construido con FastAPI + Python 3.12, gestionado con `uv`.
Hoy el código implementa **solo `GET /health`**. Estados, proyectos y tareas (v1/v2) están
**especificados pero no implementados** — implementarlos es el trabajo del curso.

## El contrato manda

`docs/contrato-api.md` es la fuente de verdad del comportamiento observable. Antes de
implementar cualquier endpoint, léelo. Puntos que no se negocian sin editar antes ese documento:

- Los códigos de estado de las tablas (`404` / `409` / `422` / `201` / `204`…) son parte del
  contrato: son lo que afirman los tests. No los cambies en el código sin cambiarlos ahí primero.
- La "Matriz Mínima de Tests" (`docs/contrato-api.md` final) enumera invariantes que los tests
  pueden ampliar pero nunca debilitar.
- Forma de error estable: clave de primer nivel siempre `detail`.
- Esquemas de respuesta exactos: los campos declarados, ni uno más ni uno menos. Un opcional
  ausente se devuelve como `null`, no se omite.
- `due_at` se serializa siempre en UTC con sufijo `Z`, sin desplazamiento `+00:00` y sin microsegundos.
- Colecciones: lista JSON en la raíz, sin objeto envolvente. Cada `GET` de colección tiene un
  orden determinista definido en el contrato.
- Normalización de `title`: se recorta y se rechaza con `422` si no queda ningún carácter visible;
  la comprobación es por categoría Unicode (`Cc`, `Cf`, `Zl`, `Zp`, `Zs`), no `strip()` a secas.
- El catálogo de estados (`PENDIENTE`, `EN_CURSO`, `BLOQUEADA`, `HECHA`) no tiene endpoints de
  escritura; llega a la base por **migración idempotente**, no por script de init de Docker.

Ante contradicción entre `README.md` y `docs/contrato-api.md`, gana el contrato.

## Comandos

Todos desde la raíz del repo. Es el "recorrido canónico" del README, en este orden:

```sh
uv sync --locked            # instala dependencias exactamente según uv.lock
uv run ruff check .         # linter (reglas E, F, I, UP, B; line-length 100)
uv run pytest -q            # suite de tests
docker compose up           # servicio db: PostgreSQL 18-alpine con healthcheck
uv run uvicorn app.main:app # sirve en http://127.0.0.1:8000 ; probar /health
docker compose down         # detiene y elimina el servicio db (conserva el volumen pgdata)
```

- Un solo test: `uv run pytest tests/test_health.py::test_health_ok`
- Recarga en desarrollo: `uv run uvicorn app.main:app --reload` (el README no lo incluye).
- `docker compose down` **no** lleva `-v`: el volumen `pgdata` sobrevive entre ejecuciones.
- No hay Makefile, justfile, `[project.scripts]` ni CI. Los comandos son estos, tal cual.

## Arquitectura

- **App ASGI**: `app.main:app` (`app/main.py`). Paquete empaquetado: `app` (ver `pyproject.toml`
  `[tool.hatch.build.targets.wheel]`).
- **Tests** (`tests/`): pytest con `asyncio_mode = "auto"`, así que las funciones `async def test_*`
  corren sin decorador. Los tests golpean la app vía `httpx.ASGITransport` en proceso, sin
  levantar servidor (ver `tests/test_health.py`).
- **Persistencia**: PostgreSQL 18 en el contenedor `db` de `compose.yaml`. Config por variables
  `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` / `POSTGRES_PORT` (ver `.env.example`;
  `compose.yaml` tiene defaults locales y funciona sin `.env`).
- Los tests de persistencia deben correr contra PostgreSQL real (no SQLite): el contrato exige
  probar rollback de v2 y re-ejecución idempotente de migraciones, que solo tienen sentido con un
  motor de migraciones real.

## Decisiones abiertas (aún sin código ni dependencia en el repo)

`pyproject.toml` y `uv.lock` no incluyen todavía ORM, driver de PostgreSQL ni herramienta de
migraciones. Al implementar hay que elegir e incorporar:

- Herramienta de migraciones con `upgrade`/`downgrade` (Alembic es lo convencional con FastAPI,
  pero no está fijado) y cómo se disparan al arrancar.
- Capa de acceso a datos (SQLAlchemy Core/ORM, SQLModel, SQL a mano).
- Driver de PostgreSQL (`psycopg` v3, `asyncpg`…) y si el acceso es sync o async. Los endpoints
  `async def` y `asyncio_mode = "auto"` sugieren async, sin confirmarlo.
- Lectura de configuración en la app (`app/main.py` hoy no lee ninguna variable de entorno).
- Base de datos y fixtures para la suite de tests.

`docs/contrato-api.md` enlaza `../docs/glosario.md#idempotente`, pero `docs/glosario.md` no existe:
crearlo o corregir el enlace.

## Secretos

- `.env` está en `.gitignore` y no se rastrea. Nunca lo fuerces al índice (`git add -f`).
- No muevas valores reales a `.env.example`, `compose.yaml`, `README.md` ni al contrato. Las
  credenciales de `compose.yaml` (`taskflow` / `taskflow_local_dev`) son solo para el contenedor
  local; un despliegue real las inyecta por entorno.
