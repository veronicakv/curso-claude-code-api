"""Esquemas de respuesta de la API.

El contrato exige los campos declarados, **ni más ni menos**: un campo de sobra
rompe a quien consuma la API igual que uno que falta.
"""

from pydantic import BaseModel, ConfigDict, field_validator

from app.text import normalizar_texto_requerido


class StateOut(BaseModel):
    """Estado tal y como lo devuelve ``GET /states``: solo ``id`` y ``code``."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: int
    code: str


class ProjectIn(BaseModel):
    """Cuerpo de ``POST /projects``. ``name`` se normaliza antes de validar."""

    model_config = ConfigDict(extra="forbid")

    name: str
    description: str | None = None

    @field_validator("name")
    @classmethod
    def _normaliza_name(cls, valor: str) -> str:
        return normalizar_texto_requerido(valor)


class ProjectOut(BaseModel):
    """Proyecto que devuelve la API: exactamente ``id``, ``name`` y ``description``."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: int
    name: str
    description: str | None


class ProjectPatch(BaseModel):
    """Cuerpo de ``PATCH /projects/{id}``: todos los campos son opcionales.

    Un campo ausente no cambia; ``description`` puede fijarse a ``null``. Anular
    ``name`` no está permitido: lo rechaza la ruta con ``422``.
    """

    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    description: str | None = None

    @field_validator("name")
    @classmethod
    def _normaliza_name(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        return normalizar_texto_requerido(valor)
