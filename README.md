# TaskFlow API

API REST de gestión de tareas construida con FastAPI, [uv](https://docs.astral.sh/uv/)
y Python 3.12, con persistencia en PostgreSQL y migraciones Alembic.

El comportamiento observable (endpoints, códigos de estado, esquemas de respuesta
y de error) está especificado en [`docs/contrato-api.md`](docs/contrato-api.md).
La aplicación ASGI se expone como `app.main:app`.

## Requisitos

- Python 3.12 (serie 3.12).
- uv.
- Docker con Compose.

## Puesta en marcha

Ejecuta estos pasos en orden, desde la raíz del repositorio:

```sh
cp .env.example .env                      # variables de PostgreSQL (valores locales ficticios)
uv sync --locked                          # instala las dependencias según uv.lock
docker compose up -d db                   # levanta PostgreSQL 18 (servicio db) con healthcheck
uv run alembic upgrade head               # crea el esquema y siembra el catálogo de estados
uv run uvicorn app.main:app               # sirve la API en http://127.0.0.1:8000
```

- `.env` no se versiona; `compose.yaml` también arranca sin él usando los mismos
  valores por defecto.
- `docker compose up -d db` deja la base en segundo plano; espera unos segundos a
  que el healthcheck la marque `healthy` antes del paso siguiente.
- `uv run alembic upgrade head` es idempotente: volver a ejecutarlo no duplica nada.
- La API queda en primer plano; déjala corriendo en esta terminal y usa otra para
  el paso siguiente. Párala con Ctrl-C.

## Probar un endpoint

Con la API corriendo, comprueba la salud:

```sh
curl http://127.0.0.1:8000/health          # -> {"status": "ok"}
```

Para ejercitar el resto de la API, [`api.http`](api.http) tiene una petición por
cada método y ruta del contrato, en un orden en el que cada una se apoya en la
anterior. Ábrelo con la extensión REST Client de VS Code (o equivalente) y lanza
los bloques de arriba abajo.

## Comprobaciones de desarrollo

```sh
uv run ruff check .                        # lint
uv run pytest -q                           # tests (contra la base PostgreSQL real; no usa SQLite)
```

`uv run pytest -q` necesita el servicio `db` levantado; si PostgreSQL no está
accesible, los tests que lo requieren fallan (no se omiten).

## Especificación OpenAPI

FastAPI genera el documento OpenAPI y lo sirve en `/openapi.json`, `/docs` y
`/redoc` con la API corriendo. El archivo [`openapi.json`](openapi.json) de la
raíz es una copia exportada; regenérala tras cambiar rutas o esquemas:

```sh
uv run python -c "import json; from app.main import app; print(json.dumps(app.openapi(), indent=2, ensure_ascii=False))" > openapi.json
```

## Parar

```sh
docker compose down                        # detiene y elimina el servicio db (el volumen pgdata se conserva)
```
