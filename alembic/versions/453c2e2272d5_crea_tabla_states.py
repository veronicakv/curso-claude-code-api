"""crea tabla states

Revision ID: 453c2e2272d5
Revises:
Create Date: 2026-09-05 19:32:47.149292

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "453c2e2272d5"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Crea la tabla ``states`` vacía, sin datos."""
    op.create_table(
        "states",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.UniqueConstraint("code", name="uq_states_code"),
    )


def downgrade() -> None:
    """Elimina la tabla ``states``."""
    op.drop_table("states")
