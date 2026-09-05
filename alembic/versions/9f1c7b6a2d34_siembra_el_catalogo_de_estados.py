"""siembra el catalogo de estados

Revision ID: 9f1c7b6a2d34
Revises: 453c2e2272d5
Create Date: 2026-09-05 19:40:16.134112

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert as pg_insert

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9f1c7b6a2d34"
down_revision: str | Sequence[str] | None = "453c2e2272d5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Catálogo fijo de estados, en el orden del contrato.
CATALOGO = [
    ("PENDIENTE", 1),
    ("EN_CURSO", 2),
    ("BLOQUEADA", 3),
    ("HECHA", 4),
]


def upgrade() -> None:
    """Inserta los 4 estados de forma idempotente.

    ``ON CONFLICT (code) DO NOTHING`` sobre la restricción única ``uq_states_code``:
    reaplicar la migración no duplica filas ni falla.
    """
    states = sa.table(
        "states",
        sa.column("code", sa.String),
        sa.column("sort_order", sa.Integer),
    )
    stmt = (
        pg_insert(states)
        .values([{"code": code, "sort_order": order} for code, order in CATALOGO])
        .on_conflict_do_nothing(index_elements=["code"])
    )
    op.execute(stmt)


def downgrade() -> None:
    """Elimina las filas sembradas, dejando la tabla vacía."""
    codes = ", ".join(f"'{code}'" for code, _ in CATALOGO)
    op.execute(f"DELETE FROM states WHERE code IN ({codes})")
