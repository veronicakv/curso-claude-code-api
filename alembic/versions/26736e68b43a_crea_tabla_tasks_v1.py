"""crea tabla tasks v1

Revision ID: 26736e68b43a
Revises: 3459cae2a91f
Create Date: 2026-09-06 06:20:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "26736e68b43a"
down_revision: str | Sequence[str] | None = "3459cae2a91f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Crea ``tasks`` (v1, sin ``due_at``).

    ``project_id`` y ``state_id`` son obligatorios y referencian ``projects`` y
    ``states`` con ``ON DELETE RESTRICT``: no hay borrado en cascada implícito.
    """
    op.create_table(
        "tasks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("state_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], name="fk_tasks_project_id", ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["state_id"], ["states.id"], name="fk_tasks_state_id", ondelete="RESTRICT"
        ),
    )


def downgrade() -> None:
    """Elimina la tabla ``tasks``."""
    op.drop_table("tasks")
