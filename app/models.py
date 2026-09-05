"""Modelos ORM de la capa de datos (SQLAlchemy 2.x)."""

from sqlalchemy import Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base declarativa común a todos los modelos."""


class State(Base):
    """Fila del catálogo de estados. El esquema lo fijan las migraciones."""

    __tablename__ = "states"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
