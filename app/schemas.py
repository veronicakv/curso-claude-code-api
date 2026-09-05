"""Esquemas de respuesta de la API.

El contrato exige los campos declarados, **ni más ni menos**: un campo de sobra
rompe a quien consuma la API igual que uno que falta.
"""

from pydantic import BaseModel, ConfigDict


class StateOut(BaseModel):
    """Estado tal y como lo devuelve ``GET /states``: solo ``id`` y ``code``."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: int
    code: str
