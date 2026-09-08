"""Esquemas de respuesta de la API.

El contrato exige los campos declarados, **ni más ni menos**: un campo de sobra
rompe a quien consuma la API igual que uno que falta.
"""

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from app.text import normalizar_texto_requerido


def _exige_zona(valor: datetime | None) -> datetime | None:
    """Normaliza ``due_at`` a UTC. Una fecha sin zona es ambigua: ``422``.

    El contrato no supone ninguna zona por su cuenta, así que un ``datetime``
    naíf (sin ``tzinfo``) se rechaza en validación.
    """
    if valor is None:
        return None
    if valor.tzinfo is None or valor.tzinfo.utcoffset(valor) is None:
        raise ValueError("due_at debe incluir zona horaria")
    return valor.astimezone(UTC)


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


class TaskIn(BaseModel):
    """Cuerpo de ``POST /tasks`` (v2). ``title`` se normaliza antes de validar.

    ``due_at`` es opcional; omitirlo conserva compatibilidad v1. Con zona
    horaria se normaliza a UTC; sin zona se rechaza con ``422``.

    ``priority`` es un entero opcional 1..3; omitirlo guarda ``null``. Un valor
    fuera de rango se rechaza con ``422``.
    """

    model_config = ConfigDict(extra="forbid")

    title: str
    description: str | None = None
    project_id: int
    state_id: int
    due_at: datetime | None = None
    priority: int | None = Field(default=None, ge=1, le=3)

    @field_validator("title")
    @classmethod
    def _normaliza_title(cls, valor: str) -> str:
        return normalizar_texto_requerido(valor)

    @field_validator("due_at")
    @classmethod
    def _normaliza_due_at(cls, valor: datetime | None) -> datetime | None:
        return _exige_zona(valor)


class TaskOut(BaseModel):
    """Tarea que devuelve la API (v2): incluye ``due_at`` y ``priority``.

    ``due_at`` se serializa siempre en UTC, con sufijo ``Z`` y sin
    microsegundos: ``2026-03-01T09:00:00Z``. Ausente se devuelve como ``null``.
    ``priority`` es ``int`` (1..3) o ``null``.
    """

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: int
    title: str
    description: str | None
    project_id: int
    state_id: int
    due_at: datetime | None
    priority: int | None

    @field_serializer("due_at")
    def _serializa_due_at(self, valor: datetime | None) -> str | None:
        if valor is None:
            return None
        return (
            valor.astimezone(UTC)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        )


class TaskPatch(BaseModel):
    """Cuerpo de ``PATCH /tasks/{id}`` (v2): todos los campos son opcionales.

    Un campo ausente no cambia; ``description``, ``due_at`` y ``priority`` pueden
    fijarse a ``null``. Anular ``title``, ``project_id`` o ``state_id`` no está
    permitido: lo rechaza la ruta con ``422``. Un ``due_at`` sin zona horaria
    también, y un ``priority`` fuera de 1..3.
    """

    model_config = ConfigDict(extra="forbid")

    title: str | None = None
    description: str | None = None
    project_id: int | None = None
    state_id: int | None = None
    due_at: datetime | None = None
    priority: int | None = Field(default=None, ge=1, le=3)

    @field_validator("title")
    @classmethod
    def _normaliza_title(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        return normalizar_texto_requerido(valor)

    @field_validator("due_at")
    @classmethod
    def _normaliza_due_at(cls, valor: datetime | None) -> datetime | None:
        return _exige_zona(valor)
