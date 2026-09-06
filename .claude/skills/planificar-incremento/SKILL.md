---
name: planificar-incremento
description: >-
  Redacta un plan de incremento para este repositorio a partir de sus documentos
  de verdad. Planifica y no implementa: no crea ni modifica código, no instala
  dependencias y no toca la base de datos. Úsala cuando el usuario pida planificar
  una capacidad, un endpoint o un cambio antes de escribir código.
---

# Planificar un incremento

Esta skill produce **un documento de plan**. No escribe código de la aplicación,
no edita `pyproject.toml` ni `uv.lock`, no ejecuta `uv sync`/`uv add`, no crea ni
corre migraciones y no se conecta a PostgreSQL. Su única salida es un archivo
Markdown nuevo en `docs/`.

## 1. Documentos contra los que se planifica

Léelos completos antes de redactar. Son las fuentes de verdad de este repo:

- `docs/contrato-api.md` — comportamiento observable: códigos de estado, esquemas
  de respuesta y de error, orden de las colecciones, normalización de `title`,
  reglas de `due_at`. El plan se ciñe a esto al pie de la letra.
- `docs/decisiones-ingenieria.md` — decisiones del equipo que no se deducen del
  código (motor de migraciones, PostgreSQL real en tests, política de tests,
  manejo de `.env`).
- `CLAUDE.md` — instrucciones del proyecto: comandos canónicos, reglas de
  persistencia, tests y secretos.
- `README.md` — comandos canónicos del repositorio y recorrido en orden.
- Planes previos en `docs/` (por ejemplo `docs/plan-persistencia.md`) — para no
  contradecir un alcance ya acordado ni redecidir lo ya decidido.

Ante contradicción entre `README.md` y `docs/contrato-api.md`, gana el contrato.
El plan **no** edita ninguno de estos documentos.

## 2. Dónde se escribe el resultado

Un archivo nuevo en `docs/`, con nombre que diga de qué es el plan:
`docs/plan-<tema>.md` (por ejemplo `docs/plan-proyectos.md`,
`docs/plan-filtros-tareas.md`). Si ya existe un archivo con ese nombre, no lo
pises: usa un nombre más específico o pregunta.

## 3. Estructura del plan

El archivo contiene, en este orden:

1. **Título y estado** — una línea que diga que es un plan acordado sin
   implementación, y el alcance en una frase.
2. **Fuentes** — los documentos de la sección 1 que aplican a este plan,
   nombrados.
3. **Fuera de alcance** — lista explícita de lo que este plan **no** cubre
   (secciones del contrato, campos, endpoints, CI, hooks, etc.). Sin esta
   sección el plan no está terminado.
4. **Archivos que no se tocan** — al menos los documentos de verdad y `.env`.
5. **Estado inicial del repositorio** — lo que hoy existe y lo que no, verificado
   en el repo (no supuesto): módulos, dependencias en `uv.lock`, migraciones
   presentes, rama.
6. **Decisiones acordadas** — cada decisión en afirmativo, con una línea de
   "por qué encaja" anclada en algo del repositorio. Ninguna decisión en
   condicional (ver sección 4).
7. **Incrementos numerados** — ver sección 5.

## 4. Ninguna decisión aplazada

El plan no contiene frases como "se podría", "quizá convenga", "una opción sería"
ni disyuntivas sin resolver. Cada punto que el plan necesita decidir queda
decidido y justificado con lo que hay en el repositorio.

Si algo **no** se puede decidir con los documentos, el código y la configuración
presentes, **pregunta al usuario** antes de terminar el plan y escribe la
respuesta como decisión firme. No lo dejes propuesto en condicional para que se
resuelva después.

## 5. Incrementos numerados con comprobación ejecutable

Los incrementos van numerados (`### Incremento 1`, `### Incremento 2`, …). Cada
incremento es del tamaño de un commit que se confirma solo.

Cada incremento declara:

- **Qué** — el cambio concreto que introduce, y qué queda explícitamente para
  después.
- **Comprobación** — pasos **ejecutables** que verifican ese incremento, no una
  descripción vaga. Con los comandos canónicos del repo:
  - `uv run ruff check .` limpio.
  - `uv run pytest -q` en verde, sin debilitar tests existentes.
  - El **test que falla primero**: una capacidad nueva empieza por un test que
    falla por la ausencia de esa capacidad; nómbralo y di qué afirma.
  - Si toca esquema: `uv run alembic upgrade head` y `uv run alembic downgrade`
    probados en ambos sentidos; `upgrade` dos veces seguidas no falla; el seed es
    idempotente.

Un incremento cuya comprobación no se puede ejecutar tal como está escrita no
está listo.

## 6. Límite de la skill

Planifica, no implementa. Si al planificar detectas que hace falta escribir
código, instalar una dependencia o correr una migración para validar una
hipótesis, **no lo hagas**: anótalo como incógnita, pregunta al usuario, o
recógelo como comprobación del incremento correspondiente para que se ejecute
cuando ese incremento se implemente.

## Cómo entregar

1. Lee los documentos de la sección 1 y verifica el estado del repo.
2. Resuelve o pregunta cada decisión pendiente (sección 4).
3. Escribe `docs/plan-<tema>.md` con la estructura de la sección 3.
4. Muéstrale al usuario la ruta del archivo y un resumen de los incrementos.
