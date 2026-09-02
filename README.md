# TaskFlow API

Base de una API FastAPI administrada con [uv](https://docs.astral.sh/uv/) y Python 3.12.

En esta primera entrega la aplicacion solo expone `GET /health`, que responde
`200` con `{"status": "ok"}`. La aplicacion ASGI se expone como `app.main:app`.

## Requisitos

- Python 3.12 (serie 3.12).
- uv.
- Docker con Compose.

## Configuracion

Las variables de PostgreSQL estan documentadas en `.env.example`. Copia ese
archivo a `.env` y ajusta los valores si lo necesitas; `compose.yaml` tambien
funciona sin `.env` usando valores locales por defecto.

## Recorrido canonico

Ejecuta estos comandos, en orden, desde la raiz del repositorio:

```sh
uv sync --locked
uv run ruff check .
uv run pytest -q
docker compose up
uv run uvicorn app.main:app
docker compose down
```

- `uv sync --locked` instala las dependencias exactamente segun `uv.lock`.
- `uv run ruff check .` pasa el linter.
- `uv run pytest -q` ejecuta la suite de tests.
- `docker compose up` levanta el servicio `db` (PostgreSQL 18-alpine) con healthcheck.
- `uv run uvicorn app.main:app` sirve la API en `http://127.0.0.1:8000`; comprueba
  `http://127.0.0.1:8000/health`.
- `docker compose down` detiene y elimina el servicio `db`.
