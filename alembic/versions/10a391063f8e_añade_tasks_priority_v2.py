"""añade tasks.priority v2

Revision ID: 10a391063f8e
Revises: c37bf9acde41
Create Date: 2026-09-07 20:48:38.725318

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "10a391063f8e"
down_revision: str | Sequence[str] | None = "c37bf9acde41"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Añade ``tasks.priority`` (v2): entero opcional con valores 1..3.

    La columna es ``NULL`` para las tareas existentes. Un ``CHECK`` garantiza el
    rango 1..3 en la base, con independencia de la validación de la aplicación.
    """
    op.add_column(
        "tasks",
        sa.Column("priority", sa.Integer(), nullable=True),
    )
    op.create_check_constraint(
        "ck_tasks_priority_rango",
        "tasks",
        "priority IS NULL OR priority BETWEEN 1 AND 3",
    )


def downgrade() -> None:
    """Elimina ``tasks.priority`` y su ``CHECK``: vuelve al esquema anterior."""
    op.drop_constraint("ck_tasks_priority_rango", "tasks", type_="check")
    op.drop_column("tasks", "priority")
