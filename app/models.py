"""Modelos ORM de la capa de datos (SQLAlchemy 2.x)."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base declarativa común a todos los modelos."""


class State(Base):
    """Fila del catálogo de estados. El esquema lo fijan las migraciones."""

    __tablename__ = "states"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)


class Project(Base):
    """Proyecto. El esquema lo fijan las migraciones."""

    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class Task(Base):
    """Tarea (v2). El esquema lo fijan las migraciones.

    ``due_at`` es opcional y se guarda con zona horaria; la aplicación lo
    normaliza a UTC antes de persistir.
    """

    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="RESTRICT"), nullable=False
    )
    state_id: Mapped[int] = mapped_column(
        ForeignKey("states.id", ondelete="RESTRICT"), nullable=False
    )
    due_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
