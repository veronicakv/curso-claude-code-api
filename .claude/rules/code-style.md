---
description: >-
  Ninguna automatización que reparta o reorganice cambios del working tree puede
  modificar el código para simular un estado intermedio; se segmenta con git add
  o git add -p.
alwaysApply: true
---

# Segmentar cambios existentes sin reescribirlos

Ninguna automatización que reparta, reorganice o reescriba cambios existentes del
working tree puede modificar el código para simular un estado intermedio.

Para segmentar cambios ya existentes se debe usar `git add` completo o
`git add -p`.
