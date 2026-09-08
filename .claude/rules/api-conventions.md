---
description: >-
  Todo endpoint nuevo o modificado sigue el esquema de respuesta exacto del
  contrato; todo campo nuevo se añade en tres capas: migración, esquema y
  validación.
paths:
  - app/
---

# Convenciones de la API

- Todo endpoint nuevo o modificado debe seguir exactamente el esquema de
  respuesta del contrato: ni campos de más ni de menos.
- Todo campo nuevo debe añadirse en tres capas: migración, esquema y validación,
  igual que `priority` en el Lab 01.
