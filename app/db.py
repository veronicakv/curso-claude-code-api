"""Conexión a PostgreSQL: URL, engine perezoso y sesión por request.

La URL se arma desde las variables ``POSTGRES_*`` (documentadas en
``.env.example``) con el dialecto ``postgresql+psycopg``; ``DATABASE_URL``, si
está definida, tiene prioridad. El engine se crea de forma perezosa la primera
vez que se necesita, nunca como efecto de importar el módulo.
"""

import os
from collections.abc import Iterator

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker


class DatabaseSettings(BaseSettings):
    """Parámetros de conexión tomados del entorno."""

    model_config = SettingsConfigDict(
        extra="ignore",
        env_file=".env",
        env_file_encoding="utf-8",
    )

    user: str = Field(alias="POSTGRES_USER")
    password: str = Field(alias="POSTGRES_PASSWORD")
    db: str = Field(alias="POSTGRES_DB")
    host: str = Field(default="localhost", alias="POSTGRES_HOST")
    port: int = Field(default=5432, alias="POSTGRES_PORT")

    @property
    def url(self) -> str:
        return (
            f"postgresql+psycopg://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.db}"
        )


def build_database_url() -> str:
    """Devuelve la URL ``postgresql+psycopg://...`` construida desde el entorno."""

    return DatabaseSettings().url


def _resolve_url() -> str:
    """``DATABASE_URL`` si está definida; si no, la armada desde ``POSTGRES_*``."""

    return os.environ.get("DATABASE_URL") or build_database_url()


_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    """Engine SQLAlchemy, creado la primera vez que se pide."""

    global _engine, _SessionLocal
    if _engine is None:
        _engine = create_engine(_resolve_url(), pool_pre_ping=True)
        _SessionLocal = sessionmaker(bind=_engine, class_=Session, expire_on_commit=False)
    return _engine


def reset_engine() -> None:
    """Descarta el engine y la factoría de sesiones (útil entre tests)."""

    global _engine, _SessionLocal
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionLocal = None


def get_session() -> Iterator[Session]:
    """Dependencia FastAPI: una sesión por request, cerrada al terminar."""

    get_engine()
    assert _SessionLocal is not None  # lo garantiza get_engine()
    session = _SessionLocal()
    try:
        yield session
    finally:
        session.close()
