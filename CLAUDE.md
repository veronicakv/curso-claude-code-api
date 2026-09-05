# CLAUDE.md

## Fuentes de verdad

- `docs/contrato-api.md` define el comportamiento observable (códigos de estado,
  esquemas de respuesta y de error, orden de colecciones, normalización de `title`,
  reglas de `due_at`). Léelo antes de implementar o modificar un endpoint y cúmplelo
  al pie de la letra.
- `docs/decisiones-ingenieria.md` recoge las decisiones de ingeniería del equipo
  que no se deducen del código.
- `README.md` tiene los comandos canónicos del repositorio.
- Ante contradicción entre `README.md` y `docs/contrato-api.md`, gana el contrato.
- El contrato solo se edita cuando el ticket dice explícitamente que lo cambia, y
  ese cambio va en un commit separado, antes de tocar tests o código.

## Comandos canónicos

Desde la raíz del repo:

```sh
uv sync --locked       # instala dependencias según uv.lock
uv run ruff check .     # lint
uv run pytest -q        # tests
```

El recorrido completo (Docker, servidor) está en `README.md`; respétalo en orden.

## Persistencia

- Las pruebas que ejercitan persistencia corren contra PostgreSQL real, nunca
  SQLite: es lo único que reproduce restricciones, tipos y migraciones.
- El esquema cambia por migraciones, no por efectos al importar módulos ni por
  script de init de Docker. Cada migración implementa `upgrade` y `downgrade` y se
  prueba en ambos sentidos antes de integrarse. El seed de estados es idempotente.

## Tests

- Una capacidad nueva empieza por un test que falla por la ausencia de esa
  capacidad.
- No se debilita ni elimina un test existente para conseguir verde. Si el
  comportamiento acordado cambió, primero cambia el contrato y luego el test, en
  un commit aparte.

## Secretos

- No abras, muestres, edites ni confirmes `.env`. Nunca `git add -f .env`.
- `.env.example` es la única fuente permitida para conocer nombres de variables.
  Los valores reales se configuran fuera de la conversación.
- No muevas valores reales a `.env.example`, `compose.yaml`, `README.md` ni al
  contrato.
