# Mapa de onboarding — TaskFlow API

Repo: `/mnt/g/cursoIA/curso-claude/curso-claude-code-api` · branch `main` · 2 commits · árbol de trabajo limpio.

## Qué es hoy

FastAPI + Python 3.12 gestionado con `uv`. Estado actual del código: solo `GET /health`. El resto de la API (estados, proyectos, tareas v1/v2) está **especificado pero no implementado** — es el trabajo del curso.

---

## 1. Fuente de verdad del comportamiento

| Hecho | Evidencia |
|---|---|
| El contrato de comportamiento observable vive en un solo documento | `docs/contrato-api.md:1-4` |
| El documento "fija comportamiento observable; la estructura interna queda abierta salvo restricciones de seguridad, migración y verificación" | `docs/contrato-api.md:3-4` |
| Los códigos de estado de las tablas son parte del contrato: "son lo que afirman los tests, y lo que la sesión 10 compara al revisar. No los cambies sin cambiar antes este documento" | `docs/contrato-api.md:11-13` |
| La "Matriz Mínima de Tests" enumera invariantes que los tests no pueden debilitar | `docs/contrato-api.md:152-167` |
| El código actual cumple solo la sección "Salud" | `app/main.py:6-8` vs `docs/contrato-api.md:44-54` |
| El README describe el mismo `GET /health` y nombra la app ASGI como `app.main:app` | `README.md:5-6` |

**Inferencia:** ante conflicto entre README y contrato, manda `docs/contrato-api.md` (el README se declara "primera entrega"; el contrato se declara norma verificable). — Confianza media, no hay una regla escrita que lo diga explícitamente.

---

## 2. Comandos exactos

Todos desde la raíz del repo. Fuente: `README.md:24-39` ("Recorrido canónico", en ese orden).

| Fase | Comando | Efecto (evidencia) |
|---|---|---|
| Instalar | `uv sync --locked` | Instala dependencias exactamente según `uv.lock` (`README.md:33`) |
| Revisar estilo | `uv run ruff check .` | Linter; reglas `E,F,I,UP,B`, line-length 100, target `py312` (`pyproject.toml:20-25`) |
| Probar | `uv run pytest -q` | Suite de tests; `asyncio_mode=auto`, `testpaths=["tests"]` (`pyproject.toml:27-29`) |
| Levantar dependencias | `docker compose up` | Servicio `db`: PostgreSQL `18-alpine` con healthcheck `pg_isready` (`compose.yaml:2-17`, `README.md:36`) |
| Ejecutar la API | `uv run uvicorn app.main:app` | Sirve en `http://127.0.0.1:8000`; verificar `http://127.0.0.1:8000/health` (`README.md:37-38`) |
| Detener dependencias | `docker compose down` | Detiene y elimina el servicio `db` (`README.md:39`) |

**Notas de evidencia:**

- `uvicorn app.main:app` en el README **no** lleva `--reload` ni `--host/--port` explícitos (`README.md:29`). El puerto 8000 es el default de uvicorn, coincide con lo que afirma el README.
- No hay `Makefile`, `justfile` ni scripts en `pyproject.toml`: los comandos son los de arriba, tal cual.
- No hay configuración de CI (`.github/` ausente).
- `docker compose down` **no** incluye `-v`, así que el volumen `pgdata` (`compose.yaml:10-11,19-20`) sobrevive entre ejecuciones. Relevante para el punto 3.

---

## 3. Motor para los tests de persistencia

| Hecho | Evidencia |
|---|---|
| El curso **adopta migración** como mecanismo para llevar el catálogo de estados a la base | `docs/contrato-api.md:70-77` — "El curso adopta la migración" |
| Razón declarada: el script de init de Docker solo corre "al crear el volumen por primera vez"; quien ya tenía el volumen "nunca recibe el catálogo" | `docs/contrato-api.md:70-77` |
| La migración debe ejecutarse "en cada `upgrade`, en cualquier entorno" | `docs/contrato-api.md:72` (tabla) |
| El seed de estados debe ser **idempotente**: "ejecutarlo dos veces deja lo mismo que una" | `docs/contrato-api.md:79-80` |
| La matriz de tests exige: "Migración desde base vacía y rollback de v2" y "migrar dos veces no lo duplica" | `docs/contrato-api.md:163-164` |
| El almacén de datos es **PostgreSQL 18** (contenedor `db`) | `compose.yaml:3` |
| Variables de conexión: `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_PORT` | `.env.example:5-14`, `compose.yaml:4-9` |

**Conclusión:** los futuros tests de persistencia deben ejercitarse contra **PostgreSQL** (no SQLite en memoria) y a través de **migraciones versionadas con `upgrade`/`downgrade`** — el contrato exige probar rollback de v2 y re-ejecución idempotente, cosas que solo tienen sentido con un motor de migraciones real.

**Desconocido:** el contrato dice "migración" pero **no nombra la herramienta**. Alembic es la opción convencional con FastAPI/SQLAlchemy, pero:

- `pyproject.toml:7-18` **no** incluye `alembic`, `sqlalchemy`, `psycopg`/`asyncpg` ni ningún cliente de base de datos.
- `uv.lock` no contiene ninguna de esas cadenas.
- No existe carpeta `alembic/`, `migrations/` ni `alembic.ini`.

Elegir e incorporar la herramienta de migraciones y el driver de PostgreSQL es una decisión abierta (ver punto 5).

---

## 4. Límites sobre archivos con secretos

| Hecho | Evidencia |
|---|---|
| `.env` está en `.gitignore` y **no está rastreado** por git | `.gitignore:1`; `git ls-files` solo devuelve `.env.example` |
| `.env.example` **sí** se versiona y contiene solo valores ficticios locales | `git ls-files` incluye `.env.example`; `.env.example:1-2` — "Valores locales ficticios para desarrollo… No pongas secretos reales aqui" |
| El `.env` local actual tiene exactamente las mismas 4 claves que `.env.example`, con los mismos valores de ejemplo (`diff` de claves vacío; valores coinciden con el example) | inspección directa de `.env` |
| El contrato prohíbe filtrar credenciales por la API: `GET /health` "No expone credenciales ni detalles internos" | `docs/contrato-api.md:54` |
| El contrato pide errores "con forma estable" `{"detail": "<mensaje>"}` sin detalles internos | `docs/contrato-api.md:14-17` |
| `compose.yaml` usa credenciales por defecto embebidas (`taskflow` / `taskflow_local_dev`) pensadas solo para local | `compose.yaml:5-7` — password literal `taskflow_local_dev` |

**Regla operativa (inferida de lo anterior):**

- Nunca `git add -f .env`; nunca mover valores reales a `.env.example`, `compose.yaml`, `README.md` ni al contrato.
- El `.env` de este checkout **no contiene secretos reales** (son los valores ficticios del ejemplo), pero trátalo como si los tuviera: no pegar su contenido en commits, PRs, issues ni logs.
- Las credenciales de `compose.yaml` son solo para el contenedor local de desarrollo; cualquier despliegue real debe inyectarlas por entorno, no por el archivo versionado.

---

## 5. Decisiones que no puedo establecer con evidencia

| # | Decisión abierta | Por qué queda abierta |
|---|---|---|
| D1 | **Herramienta de migraciones** (¿Alembic? ¿otra?) y su layout (`alembic/`, `alembic.ini`, `env.py`). | El contrato exige "migración" con `upgrade`/`downgrade` y rollback de v2 (`contrato-api.md:70-77,163`), pero no nombra herramienta y no hay ninguna en `pyproject.toml`/`uv.lock`. |
| D2 | **ORM / capa de acceso a datos** (SQLAlchemy Core, SQLAlchemy ORM, SQLModel, `databases`, SQL a mano). | `docs/contrato-api.md:3-4` deja "la estructura interna abierta"; no hay ninguna dependencia de datos instalada. |
| D3 | **Driver de PostgreSQL** (`psycopg` v3, `psycopg2`, `asyncpg`) y si el acceso será sync o async. | El único indicio de async es `asyncio_mode=auto` en pytest y los endpoints `async def`; no hay driver en el lock. |
| D4 | **Cómo se disparan las migraciones al arrancar** (comando manual `alembic upgrade head`, hook de startup en FastAPI, entrypoint de Docker). | El contrato dice "en cada `upgrade`, en cualquier entorno" (`contrato-api.md:72`) pero no fija el mecanismo; el README no incluye ningún comando de migración. |
| D5 | **Config de conexión en la app** (Pydantic Settings, `os.environ` directo, `pydantic-settings`). | Solo existen las variables `POSTGRES_*` en `.env.example`; `app/main.py` no lee configuración alguna. |
| D6 | **`docs/glosario.md`** — el contrato enlaza `../docs/glosario.md#idempotente` (`contrato-api.md:79`) pero el archivo **no existe** (`ls docs/` → solo `contrato-api.md` y este archivo). Falta crearlo o corregir el enlace. |
| D7 | **Base de datos para la suite de tests**: ¿la misma instancia Docker `db`, una base separada, fixtures que crean/tumban esquema por test? No hay configuración de test-db ni fixtures (`tests/` solo tiene `test_health.py` y un `__init__.py` vacío). |
| D8 | **Estrategia de puerto/URL de la app** en producción/CI: el README solo cubre `127.0.0.1:8000` local sin `--host 0.0.0.0`. |
| D9 | **Precedencia formal README ↔ contrato** ante contradicción (asumida a favor del contrato, sin regla escrita). |

---

## Apéndice: separación hechos / inferencias / desconocidos

**Hechos (con archivo:línea, verificados en este checkout):**

- Código implementado = `GET /health` solamente. `app/main.py:6-8`
- App ASGI = `app.main:app`. `app/main.py:3`, `README.md:6`
- Python `>=3.12,<3.13`. `pyproject.toml:6`
- Deps runtime: `fastapi>=0.115`, `uvicorn[standard]>=0.30`. `pyproject.toml:7-10`
- Deps dev: `pytest>=8.3`, `pytest-asyncio>=0.24`, `httpx>=0.27`, `ruff>=0.6`. `pyproject.toml:12-18`
- Ruff: line-length 100, reglas `E,F,I,UP,B`. `pyproject.toml:20-25`
- Pytest: `asyncio_mode=auto`, `testpaths=["tests"]`. `pyproject.toml:27-29`
- DB: `postgres:18-alpine`, volumen `pgdata`, healthcheck `pg_isready`. `compose.yaml:2-20`
- `.env` ignorado y no rastreado; `.env.example` versionado con valores ficticios. `.gitignore:1`, `.env.example:1-2`, `git ls-files`
- El contrato adopta: migración para el seed de estados, seed idempotente, `409` al borrar proyecto con tareas, `422` para texto sin carácter visible (chequeo por categoría Unicode `Cc/Cf/Zl/Zp/Zs`), `due_at` siempre en UTC con `Z` sin microsegundos, colecciones como lista JSON en la raíz, esquema de respuesta exacto. `contrato-api.md:20-28,70-80,92-95,110-113,144-150`
- Órdenes deterministas por endpoint. `contrato-api.md:38-42`
- No hay CI, Makefile, ni scripts de tarea. (ausencia de `.github/`, `Makefile`, `[project.scripts]`)

**Inferencias (razonadas, no escritas):**

- Ante conflicto README/contrato, gana el contrato (D9).
- Los tests de persistencia deben correr contra PostgreSQL real, no SQLite, porque el contrato exige probar rollback e idempotencia de migraciones (deriva de `contrato-api.md:79-80,163-164` + `compose.yaml:3`).
- Alembic es la herramienta de migraciones más probable por convención FastAPI, pero no está confirmada.
- El acceso a datos probablemente será async (endpoints `async def` + `asyncio_mode=auto`), sin confirmación.

**Desconocidos (sin evidencia en el repo):** D1–D8 de la tabla anterior — herramienta de migraciones, ORM, driver PG, disparo de migraciones, config de conexión, `docs/glosario.md` faltante, DB de tests, y exposición de host en despliegue.
