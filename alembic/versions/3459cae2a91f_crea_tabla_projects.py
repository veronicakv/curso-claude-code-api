"""crea tabla projects

Revision ID: 3459cae2a91f
Revises: 9f1c7b6a2d34
Create Date: 2026-09-06 00:58:57.145565

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3459cae2a91f"
down_revision: str | Sequence[str] | None = "9f1c7b6a2d34"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Crea la tabla ``projects``: ``name`` obligatorio, ``description`` opcional."""
    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    """Elimina la tabla ``projects``."""
    op.drop_table("projects")
