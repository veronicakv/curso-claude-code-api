"""Pruebas del endpoint ``GET /states`` contra PostgreSQL real.

Requieren la instancia de ``compose.yaml`` accesible y la base de datos dedicada
a tests, migrada a ``head``. Si PostgreSQL no está accesible, estas pruebas
fallan; no se hace skip para conseguir verde.
"""

import os
import subprocess
from collections.abc import Iterator

import httpx
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

TEST_DB = "taskflow_test"
CATALOGO_ESTADOS = ["PENDIENTE", "EN_CURSO", "BLOQUEADA", "HECHA"]


def _url_for(db_name: str) -> str:
    user = os.environ.get("POSTGRES_USER", "taskflow")
    password = os.environ.get("POSTGRES_PASSWORD", "taskflow_local_dev")
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{db_name}"


def _test_db_url() -> str:
    return _url_for(TEST_DB)


def _admin_url() -> str:
    return _url_for(os.environ.get("POSTGRES_DB", "taskflow"))


@pytest.fixture()
def client() -> Iterator[httpx.AsyncClient]:
    """Cliente ASGI con la sesión de BD apuntando a la base de test migrada.

    Crea ``taskflow_test`` si no existe, la lleva a ``head`` (lo que siembra el
    catálogo) y sobreescribe la dependencia de sesión de la app para que use
    esa base. No toca la base principal.
    """
    admin = create_engine(_admin_url(), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": TEST_DB}
        ).scalar()
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{TEST_DB}"'))
    admin.dispose()

    engine = create_engine(_test_db_url())
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS alembic_version"))
        conn.execute(text("DROP TABLE IF EXISTS states"))

    env = dict(os.environ)
    env["DATABASE_URL"] = _test_db_url()
    subprocess.run(
        ["uv", "run", "alembic", "upgrade", "head"],
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )

    from app.main import app, get_session

    TestSession = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)

    def _session_override() -> Iterator[Session]:
        session = TestSession()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_session] = _session_override

    transport = httpx.ASGITransport(app=app)
    async_client = httpx.AsyncClient(transport=transport, base_url="http://testserver")

    yield async_client

    app.dependency_overrides.clear()
    engine.dispose()


async def test_get_states_devuelve_lista_de_id_y_code_en_orden(
    client: httpx.AsyncClient,
) -> None:
    async with client:
        response = await client.get("/states")

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list), "el cuerpo debe ser una lista JSON en la raíz"
    assert len(body) == 4
    for item in body:
        assert set(item.keys()) == {"id", "code"}, "cada elemento: exactamente id y code"
        assert isinstance(item["id"], int)
        assert isinstance(item["code"], str)
    assert [item["code"] for item in body] == CATALOGO_ESTADOS


async def test_get_states_dos_llamadas_identicas_mismos_ids_en_la_misma_posicion(
    client: httpx.AsyncClient,
) -> None:
    async with client:
        primera = (await client.get("/states")).json()
        segunda = (await client.get("/states")).json()

    assert [item["id"] for item in primera] == [item["id"] for item in segunda]


@pytest.mark.parametrize("method", ["POST", "DELETE"])
async def test_states_no_admite_post_ni_delete(
    client: httpx.AsyncClient, method: str
) -> None:
    async with client:
        response = await client.request(method, "/states")

    assert response.status_code == 405, f"{method} /states no debe existir"
