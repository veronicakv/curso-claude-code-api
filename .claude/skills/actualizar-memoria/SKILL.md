---
name: actualizar-memoria
description: >-
  Revisa el estado real del repositorio y la conversación, y actualiza la
  memoria persistente de Claude Code (los archivos en el directorio memory/ del
  proyecto y su índice MEMORY.md) para que reflejen lo aprendido. No modifica el
  repositorio ni el código: su única salida son los archivos de memoria. Úsala
  cuando el usuario pida "actualiza las memorias", "guarda el contexto" o
  "recuerda lo que aprendimos hasta ahora".
---

# Actualizar la memoria del proyecto

Esta skill escribe **la memoria de Claude Code** y, cuando lo aprendido lo
justifica, **`CLAUDE.md`**. No toca nada más del repositorio: no edita el
contrato ni `docs/`, ni el código, ni `.claude/rules/` o skills, no ejecuta
migraciones ni `git commit`, y **nunca** abre ni edita `.env`. Su salida son los
`.md` del directorio de memoria, su índice `MEMORY.md` y, si procede, `CLAUDE.md`.

## 1. Dónde vive la memoria

- Directorio: `<CLAUDE_PROJECT_MEMORY_DIR>` — el directorio `memory/` bajo la
  carpeta de proyecto de Claude Code (la misma ruta que aparece en el
  system-prompt de esta sesión). Ya existe; escribe con la herramienta Write.
- Un archivo = un hecho, con frontmatter `name` / `description` / `metadata.type`
  (`user` | `feedback` | `project` | `reference`).
- `MEMORY.md` es el índice que se carga cada sesión: una línea por memoria
  (`- [Título](archivo.md) — gancho`), sin contenido de la memoria dentro.

## 2. Reúne lo aprendido (antes de escribir nada)

Contrasta la memoria actual con la realidad. No supongas: verifica.

1. **Lee toda la memoria existente**: `MEMORY.md` y cada `.md` del directorio.
2. **Estado real del repo**:
   - `git log --oneline <última-fecha-de-memoria>..HEAD` — commits nuevos.
   - `git status` y rama actual.
   - `git show --stat <commit>` en los commits relevantes.
   - Cambios en `.claude/` (skills, rules, settings), en `docs/` y en migraciones
     (`alembic/versions/`, head actual).
3. **La conversación en curso**: decisiones tomadas, correcciones del usuario,
   preferencias expresadas, rechazos justificados, trabajo terminado y verificado.
4. **Fuentes de verdad del repo** si hay dudas de comportamiento:
   `docs/contrato-api.md` (gana sobre `README.md`), `docs/decisiones-ingenieria.md`,
   `CLAUDE.md`.
5. **Lo que ya dice `CLAUDE.md`**: léelo entero y anota qué afirmaciones han
   quedado desactualizadas o incompletas por lo aprendido (comandos, rutas,
   convenciones de proceso, estado de capacidades).

## 3. Decide qué guardar

Guarda solo lo que **no** se deduce ya del repo y **sí** importa más allá de esta
conversación:

- `user` — quién es el usuario (rol, expertise, preferencias estables).
- `feedback` — cómo quiere el usuario que trabajes (correcciones y enfoques
  confirmados). Incluye el **porqué**.
- `project` — trabajo en curso, objetivos, restricciones y estado que no salen
  del código ni del historial. Fechas relativas → absolutas.
- `reference` — punteros a recursos externos (URLs, tickets, dashboards).

**No** guardes lo que el repo ya registra (estructura del código, fixes pasados,
historial de Git, `CLAUDE.md`) ni lo que solo sirve para esta conversación. Si el
usuario pide recordar algo así, pregunta qué fue lo no obvio y guarda eso.

Para cada candidato, busca primero un archivo existente que ya lo cubra:
**actualiza ese archivo** en vez de duplicar. Borra las memorias que resultaron
falsas.

## 4. ¿Toca actualizar `CLAUDE.md`?

`CLAUDE.md` son las instrucciones de proyecto que se cargan cada sesión.
Actualízalo cuando lo aprendido cambie algo que ahí está escrito y que todo
colaborador necesita saber desde el arranque:

- un comando canónico cambió o falta,
- una regla de proceso nueva y estable (no una preferencia puntual),
- una ruta o nombre de archivo que `CLAUDE.md` menciona y ya no existe,
- una sección que contradice el estado real del repo.

**No** lo toques para: detalle efímero de la conversación, estado de avance
(eso va en memoria `project`), ni nada que ya viva en `docs/contrato-api.md`,
`docs/decisiones-ingenieria.md` o `.claude/rules/` — en ese caso el cambio va en
su archivo, no en `CLAUDE.md`, y probablemente fuera del alcance de esta skill.

Edición mínima y quirúrgica: cambia solo las líneas afectadas, respeta el tono y
la estructura del archivo. Nunca muevas valores reales de `.env` a `CLAUDE.md`.

## 5. Forma de cada archivo de memoria

```
---
name: <slug-en-kebab-case>
description: <una línea; se usa para decidir relevancia al recordar>
metadata:
  type: user | feedback | project | reference
---

<el hecho. Para feedback/project, sigue con líneas **Why:** y **How to apply:**.
Enlaza memorias relacionadas con [[su-name]].>
```

Enlaza con generosidad: un `[[name]]` que aún no existe marca algo que vale la
pena escribir después, no es un error.

## 6. Antes de escribir: enseña los borradores

Este repo pide ver el contenido propuesto **antes** de guardarlo (ver la memoria
`mostrar-antes-de-guardar`). Muestra en el chat, agrupados:

- los archivos **nuevos** (contenido completo),
- los archivos **reescritos** (contenido completo o el diff claro),
- el diff propuesto de `CLAUDE.md`, si lo hay,
- las líneas nuevas o cambiadas de `MEMORY.md`.

Espera el visto bueno explícito del usuario. No encadenes redactar + guardar en
un solo paso salvo que lo pida.

## 7. Escribe

1. Write de cada `.md` nuevo o actualizado en el directorio de memoria.
2. Si procede, Edit de `CLAUDE.md` con los cambios aprobados.
3. Actualiza `MEMORY.md`: una línea por memoria nueva; ajusta el gancho de las
   que cambiaron; quita las que borraste.
4. Resume al usuario, en una tabla, qué archivo cambió y por qué.
