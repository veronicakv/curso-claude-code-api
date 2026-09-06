"""Configuración de la conexión a PostgreSQL.

Lee las variables ``POSTGRES_*`` del entorno (documentadas en ``.env.example``) y
arma la URL de conexión con el dialecto ``postgresql+psycopg``. Todavía no crea
engine ni sesión: eso llega en incrementos posteriores.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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
