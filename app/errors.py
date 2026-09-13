"""Manejo de errores de dominio, centralizado en un único lugar.

Las rutas lanzan estas excepciones en vez de `HTTPException` directamente.
`app/main.py` registra los `exception_handler` que las traducen a la forma
estable que fija el contrato: `{"detail": "<mensaje>"}`.

Esto no toca el `RequestValidationError` de FastAPI/Pydantic: los `422` que
genera el framework al validar el esquema de entrada siguen su camino por
defecto, tal y como el contrato lo permite explícitamente.
"""

from fastapi import Request
from fastapi.responses import JSONResponse


class DomainError(Exception):
    """Base de las excepciones de dominio traducibles a una respuesta HTTP."""

    status_code: int

    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class NotFoundError(DomainError):
    """Recurso o referencia inexistente: se traduce a `404`."""

    status_code = 404


class ConflictError(DomainError):
    """Conflicto con el estado actual del recurso: se traduce a `409`."""

    status_code = 409


class UnprocessableEntityError(DomainError):
    """Entrada inválida detectada a mano en la ruta: se traduce a `422`."""

    status_code = 422


def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
