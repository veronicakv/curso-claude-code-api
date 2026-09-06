---
name: segmentar-commits
description: >-
  Reparte los cambios sin confirmar del árbol de trabajo en una secuencia de
  commits con una sola intención cada uno. Parte del estado real del repositorio
  (git status y git diff --stat inyectados, no el diff completo), propone el
  reparto y espera aprobación antes de confirmar nada. Úsala cuando haya trabajo
  mezclado en el árbol y quieras un historial limpio.
---

# Segmentar en commits

Esta skill **redacta un reparto en commits y espera tu aprobación**. No ejecuta
`git add` ni `git commit` por su cuenta, no hace `push`, no reescribe historia ya
publicada y no descarta cambios. Si el árbol está limpio, lo dice y termina.

## 1. Parte del estado real, no del supuesto

Lo primero, siempre, es leer el estado del árbol **en el momento de invocar la
skill**:

- `git status --short` — el mapa: qué archivos, y en qué estado cada uno
  (staged, modificado, sin seguimiento).
- `git diff --stat HEAD` — la magnitud del cambio por archivo de lo ya seguido.

!`git status --short`

!`git diff --stat HEAD`

Eso es lo que necesitas para decidir el reparto: qué archivos hay, cómo se
agrupan, cuánto cambió cada uno y qué es nuevo frente a modificado. **No inyectes
el diff completo:** el contenido de los hunks no hace falta para agrupar por
intención, y su tamaño crece con el cambio justo cuando más falta hace segmentar.

Si —y solo si— una línea del resumen parece mezclar dos intenciones (mucho
cambio, archivo de propósito general, varias zonas tocadas), abre ese archivo o
pide su diff acotado (`git diff -- <archivo>`) para ver si hay que partirlo por
hunks. Detalle bajo demanda, archivo por archivo, nunca todo por adelantado.

No des por hecho lo que "debería" haber cambiado según la conversación: manda lo
que devuelven los comandos.

## 2. Un commit, una intención

- Cada commit hace **una sola cosa**: una capacidad, un arreglo, un renombrado,
  un ajuste de documentación, una migración. Si el mensaje necesita un "y" para
  describir el commit, probablemente son dos.
- Un mismo archivo puede repartirse entre commits (staging por hunks) si mezcla
  intenciones. Un cambio pequeño y transversal que varias piezas necesitan (por
  ejemplo un import) va con el primer commit que lo requiere.
- No mezcles cambio de comportamiento con reformateo o renombrado masivo en el
  mismo commit.

## 3. Orden con estados comprobables

Ordena los commits para que, aplicado cada uno, el repositorio quede en un estado
que **se pueda comprobar**:

- Nada de commits que dejen el árbol con imports rotos, sin construir o con tests
  en rojo por media funcionalidad.
- Lo que otros commits necesitan va antes: la migración antes del endpoint que la
  usa; la corrección de un plan o del contrato antes del código que lo cumple; el
  helper antes de su primer uso.
- Los tests van **en el mismo commit** que el código que ejercitan, no en uno
  aparte después.
- Di, para cada commit, con qué se comprueba —los comandos canónicos del repo:
  lint y tests— aunque la ejecución quede para después de tu aprobación.

## 4. Conventional Commits elegidos por intención

El prefijo describe **qué hace el commit**, no qué tipo de archivo toca:

- `feat:` — añade una capacidad observable.
- `fix:` — corrige un comportamiento incorrecto.
- `docs:` — cambia solo documentación o su equivalente (un plan, el contrato).
- `refactor:` — reordena sin cambiar comportamiento.
- `test:` — añade o ajusta pruebas sin tocar producción.
- `chore:` — tooling, configuración, dependencias.

Un commit que solo toca un `.md` pero cuya intención es habilitar una capacidad
puede no ser `docs:`; un commit que solo toca `.py` pero únicamente reordena es
`refactor:`, no `feat:`. La pregunta es "¿qué consigue este commit?", nunca "¿qué
extensión tienen sus archivos?".

Cuerpo del mensaje: qué cambia y por qué, en prosa breve. Respeta la convención
de pie de commit que ya use el repositorio (mírala con `git log`).

## 5. Aprobación antes de confirmar

Presenta el reparto completo —para cada commit: archivos (y hunks si aplica),
prefijo, mensaje propuesto y con qué se comprueba— y **espera aprobación
explícita**. No ejecutas `git add` ni `git commit` hasta que se apruebe. Si se
piden cambios, reajusta y vuelve a presentar.

## Cómo entregar

1. Inyecta `git status --short` y `git diff --stat HEAD`; lee el mapa.
2. Agrupa los cambios por intención; abre archivos concretos solo si el resumen
   no basta para decidir si hay que partirlos.
3. Ordena los grupos para que cada commit deje un estado comprobable.
4. Redacta prefijo y mensaje de cada commit según su intención.
5. Presenta el reparto y espera aprobación. Solo entonces confirmas, un commit
   cada vez.
