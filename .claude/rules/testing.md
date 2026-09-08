---
description: >-
  Antes de corregir un fallo reportado, se reproduce primero con un caso real
  contra el sistema; la reproducción se conserva después de corregir.
alwaysApply: true
---

# Reproducir antes de corregir

Antes de corregir cualquier fallo reportado, primero se reproduce con un caso
real contra el sistema. Después se hace la corrección.

La reproducción puede ser:

- un test que se ejecuta en rojo, o
- una ejecución real que deja evidencia del fallo.

La reproducción no se oculta ni se elimina después de corregir. Si se escribió un
test para reproducir el fallo, ese test permanece en la suite.
