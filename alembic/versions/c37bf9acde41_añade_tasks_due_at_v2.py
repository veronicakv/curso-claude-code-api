"""añade tasks.due_at v2

Revision ID: c37bf9acde41
Revises: 26736e68b43a
Create Date: 2026-09-07 19:31:27.981761

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c37bf9acde41"
down_revision: str | Sequence[str] | None = "26736e68b43a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Añade ``tasks.due_at`` (v2): opcional y con zona horaria.

    Se guarda como ``TIMESTAMP WITH TIME ZONE``; la aplicación normaliza a UTC
    antes de persistir. La columna es ``NULL`` para las tareas v1 existentes.
    """
    op.add_column(
        "tasks",
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    """Elimina ``tasks.due_at``: vuelve al esquema v1."""
    op.drop_column("tasks", "due_at")
