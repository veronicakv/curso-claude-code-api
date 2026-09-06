"""Pruebas del recurso Tareas (v1) contra PostgreSQL real.

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
    """Cliente ASGI con la sesión de BD apuntando a la base de test migrada."""
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
        conn.execute(text("DROP TABLE IF EXISTS tasks"))
        conn.execute(text("DROP TABLE IF EXISTS alembic_version"))
        conn.execute(text("DROP TABLE IF EXISTS states"))
        conn.execute(text("DROP TABLE IF EXISTS projects"))

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


TASK_KEYS_V1 = {"id", "title", "description", "project_id", "state_id"}


async def _crear_proyecto(client: httpx.AsyncClient, name: str = "Casa") -> int:
    return (await client.post("/projects", json={"name": name})).json()["id"]


async def _un_state_id(client: httpx.AsyncClient) -> int:
    return (await client.get("/states")).json()[0]["id"]


# --- Incremento 2 (v1): POST /tasks y GET /tasks/{id} -----------------------


async def test_post_crea_y_get_por_id(client: httpx.AsyncClient) -> None:
    async with client:
        pid = await _crear_proyecto(client)
        sid = await _un_state_id(client)

        creado = await client.post(
            "/tasks", json={"title": "Regar", "project_id": pid, "state_id": sid}
        )
        assert creado.status_code == 201
        cuerpo = creado.json()
        assert set(cuerpo.keys()) == TASK_KEYS_V1
        assert isinstance(cuerpo["id"], int) and cuerpo["id"] > 0
        assert cuerpo["title"] == "Regar"
        assert cuerpo["description"] is None
        assert cuerpo["project_id"] == pid
        assert cuerpo["state_id"] == sid

        obtenido = await client.get(f"/tasks/{cuerpo['id']}")
        assert obtenido.status_code == 200
        assert set(obtenido.json().keys()) == TASK_KEYS_V1


async def test_post_project_id_inexistente_es_404(client: httpx.AsyncClient) -> None:
    async with client:
        sid = await _un_state_id(client)
        respuesta = await client.post(
            "/tasks", json={"title": "X", "project_id": 9999, "state_id": sid}
        )
    assert respuesta.status_code == 404
    assert "detail" in respuesta.json()


async def test_post_state_id_inexistente_es_404(client: httpx.AsyncClient) -> None:
    async with client:
        pid = await _crear_proyecto(client)
        respuesta = await client.post(
            "/tasks", json={"title": "X", "project_id": pid, "state_id": 9999}
        )
    assert respuesta.status_code == 404
    assert "detail" in respuesta.json()


@pytest.mark.parametrize("title", ["   ", "​"])
async def test_post_title_vacio_o_invisible_es_422(
    client: httpx.AsyncClient, title: str
) -> None:
    async with client:
        pid = await _crear_proyecto(client)
        sid = await _un_state_id(client)
        respuesta = await client.post(
            "/tasks", json={"title": title, "project_id": pid, "state_id": sid}
        )
    assert respuesta.status_code == 422
    assert "detail" in respuesta.json()


async def test_post_clave_desconocida_es_422(client: httpx.AsyncClient) -> None:
    async with client:
        pid = await _crear_proyecto(client)
        sid = await _un_state_id(client)
        respuesta = await client.post(
            "/tasks",
            json={"title": "X", "project_id": pid, "state_id": sid, "prioridad": 1},
        )
    assert respuesta.status_code == 422
    assert "detail" in respuesta.json()


async def test_post_sin_campos_obligatorios_es_422(client: httpx.AsyncClient) -> None:
    async with client:
        respuesta = await client.post("/tasks", json={"title": "X"})
    assert respuesta.status_code == 422
    assert "detail" in respuesta.json()


async def test_get_task_inexistente_es_404(client: httpx.AsyncClient) -> None:
    async with client:
        respuesta = await client.get("/tasks/9999")
    assert respuesta.status_code == 404
    assert "detail" in respuesta.json()


async def test_get_task_id_no_entero_es_422(client: httpx.AsyncClient) -> None:
    async with client:
        respuesta = await client.get("/tasks/abc")
    assert respuesta.status_code == 422
