"""Pruebas de las migraciones de Alembic contra PostgreSQL real.

Requieren la instancia de ``compose.yaml`` accesible y una base de datos
dedicada para tests. Si PostgreSQL no está accesible, estas pruebas fallan;
no se hace skip para conseguir verde.
"""

import os
import subprocess
from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine, inspect, text

TEST_DB = "taskflow_test"

CATALOGO_ESTADOS = ["PENDIENTE", "EN_CURSO", "BLOQUEADA", "HECHA"]

# Revisión base (crea la tabla) y revisión que introduce el seed idempotente.
BASE_REVISION = "453c2e2272d5"
SEED_REVISION = "9f1c7b6a2d34"


def _admin_url() -> str:
    user = os.environ.get("POSTGRES_USER", "taskflow")
    password = os.environ.get("POSTGRES_PASSWORD", "taskflow_local_dev")
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    default_db = os.environ.get("POSTGRES_DB", "taskflow")
    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{default_db}"


def _test_db_url() -> str:
    user = os.environ.get("POSTGRES_USER", "taskflow")
    password = os.environ.get("POSTGRES_PASSWORD", "taskflow_local_dev")
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{TEST_DB}"


def _run_alembic(*args: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["DATABASE_URL"] = _test_db_url()
    return subprocess.run(
        ["uv", "run", "alembic", *args],
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )


@pytest.fixture()
def clean_test_db() -> Iterator[None]:
    """Deja la base de test creada y sin migraciones aplicadas."""
    admin = create_engine(_admin_url(), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": TEST_DB}
        ).scalar()
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{TEST_DB}"'))
    admin.dispose()

    engine = create_engine(_test_db_url(), isolation_level="AUTOCOMMIT")
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS alembic_version"))
        conn.execute(text("DROP TABLE IF EXISTS states"))
    engine.dispose()

    yield

    engine = create_engine(_test_db_url(), isolation_level="AUTOCOMMIT")
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS alembic_version"))
        conn.execute(text("DROP TABLE IF EXISTS states"))
    engine.dispose()


def _has_table(name: str) -> bool:
    engine = create_engine(_test_db_url())
    try:
        return inspect(engine).has_table(name)
    finally:
        engine.dispose()


def _codes_en_orden() -> list[str]:
    engine = create_engine(_test_db_url())
    try:
        with engine.connect() as conn:
            rows = conn.execute(
                text("SELECT code FROM states ORDER BY sort_order, id")
            ).scalars().all()
        return list(rows)
    finally:
        engine.dispose()


def _cuenta_filas() -> int:
    engine = create_engine(_test_db_url())
    try:
        with engine.connect() as conn:
            return conn.execute(text("SELECT count(*) FROM states")).scalar_one()
    finally:
        engine.dispose()


def test_upgrade_head_crea_states_y_downgrade_base_la_elimina(clean_test_db: None) -> None:
    assert not _has_table("states")

    _run_alembic("upgrade", "head")
    assert _has_table("states"), "upgrade head debe crear la tabla states"

    _run_alembic("downgrade", "base")
    assert not _has_table("states"), "downgrade base debe eliminar la tabla states"


def test_upgrade_head_dos_veces_seguidas_no_falla(clean_test_db: None) -> None:
    _run_alembic("upgrade", "head")
    # La segunda vez no debe fallar: ya está en head.
    result = _run_alembic("upgrade", "head")
    assert result.returncode == 0
    assert _has_table("states")


def test_seed_deja_los_cuatro_codes_en_el_orden_del_catalogo(clean_test_db: None) -> None:
    _run_alembic("upgrade", "head")

    assert _codes_en_orden() == CATALOGO_ESTADOS


def test_seed_es_idempotente_dos_veces_deja_cuatro_filas(clean_test_db: None) -> None:
    _run_alembic("upgrade", "head")
    assert _cuenta_filas() == 4

    # Correr el upgrade del seed una segunda vez SIN vaciar la tabla: se rebobina
    # solo el puntero de versión (stamp, no toca datos) y se vuelve a aplicar.
    # El ON CONFLICT DO NOTHING no debe duplicar filas: 4, no 8.
    _run_alembic("stamp", BASE_REVISION)
    _run_alembic("upgrade", SEED_REVISION)

    assert _cuenta_filas() == 4
    assert _codes_en_orden() == CATALOGO_ESTADOS


def test_downgrade_de_la_revision_de_seed_vacia_la_tabla_y_upgrade_la_repuebla(
    clean_test_db: None,
) -> None:
    _run_alembic("upgrade", "head")
    assert _cuenta_filas() == 4

    _run_alembic("downgrade", BASE_REVISION)
    assert _has_table("states"), "downgrade del seed no debe eliminar la tabla"
    assert _cuenta_filas() == 0, "downgrade del seed debe vaciar la tabla"

    _run_alembic("upgrade", SEED_REVISION)
    assert _codes_en_orden() == CATALOGO_ESTADOS
