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


# --- Incremento 3 (v1): GET /tasks con filtros project_id y state_id -------


async def _crear_tarea(
    client: httpx.AsyncClient, title: str, project_id: int, state_id: int
) -> int:
    respuesta = await client.post(
        "/tasks", json={"title": title, "project_id": project_id, "state_id": state_id}
    )
    return respuesta.json()["id"]


async def test_get_tasks_filtros_solos_y_combinados(client: httpx.AsyncClient) -> None:
    async with client:
        p1 = await _crear_proyecto(client, "P1")
        p2 = await _crear_proyecto(client, "P2")
        estados = (await client.get("/states")).json()
        s1, s2 = estados[0]["id"], estados[1]["id"]

        t_p1s1 = await _crear_tarea(client, "a", p1, s1)
        t_p1s2 = await _crear_tarea(client, "b", p1, s2)
        t_p2s1 = await _crear_tarea(client, "c", p2, s1)

        todas = await client.get("/tasks")
        assert todas.status_code == 200
        ids = [t["id"] for t in todas.json()]
        assert ids == sorted(ids) == [t_p1s1, t_p1s2, t_p2s1]

        por_proyecto = (await client.get("/tasks", params={"project_id": p1})).json()
        assert {t["id"] for t in por_proyecto} == {t_p1s1, t_p1s2}

        por_estado = (await client.get("/tasks", params={"state_id": s1})).json()
        assert {t["id"] for t in por_estado} == {t_p1s1, t_p2s1}

        combinado = (
            await client.get("/tasks", params={"project_id": p1, "state_id": s1})
        ).json()
        assert [t["id"] for t in combinado] == [t_p1s1]


async def test_get_tasks_dos_llamadas_identicas_mismo_orden(
    client: httpx.AsyncClient,
) -> None:
    async with client:
        pid = await _crear_proyecto(client)
        sid = await _un_state_id(client)
        for n in ("a", "b", "c"):
            await _crear_tarea(client, n, pid, sid)

        primera = [t["id"] for t in (await client.get("/tasks")).json()]
        segunda = [t["id"] for t in (await client.get("/tasks")).json()]
        con_filtro_1 = [
            t["id"] for t in (await client.get("/tasks", params={"project_id": pid})).json()
        ]
        con_filtro_2 = [
            t["id"] for t in (await client.get("/tasks", params={"project_id": pid})).json()
        ]
    assert primera == segunda
    assert con_filtro_1 == con_filtro_2


async def test_get_tasks_filtro_sin_resultados_lista_vacia(
    client: httpx.AsyncClient,
) -> None:
    async with client:
        pid = await _crear_proyecto(client, "ConTareas")
        sid = await _un_state_id(client)
        await _crear_tarea(client, "x", pid, sid)
        vacio_pid = await _crear_proyecto(client, "SinTareas")

        respuesta = await client.get("/tasks", params={"project_id": vacio_pid})
    assert respuesta.status_code == 200
    assert respuesta.json() == []


async def test_get_tasks_filtro_no_entero_es_422(client: httpx.AsyncClient) -> None:
    async with client:
        respuesta = await client.get("/tasks", params={"project_id": "abc"})
    assert respuesta.status_code == 422


async def test_get_tasks_es_lista_en_la_raiz(client: httpx.AsyncClient) -> None:
    async with client:
        respuesta = await client.get("/tasks")
    assert respuesta.status_code == 200
    assert isinstance(respuesta.json(), list)


# --- Incremento 4 (v1): PATCH /tasks/{id} y DELETE /tasks/{id} -------------


async def test_patch_parcial_consistente(client: httpx.AsyncClient) -> None:
    async with client:
        pid = await _crear_proyecto(client)
        estados = (await client.get("/states")).json()
        s1, s2 = estados[0]["id"], estados[1]["id"]
        tid = await _crear_tarea(client, "Regar", pid, s1)

        solo_desc = await client.patch(f"/tasks/{tid}", json={"description": "con manguera"})
        assert solo_desc.status_code == 200
        cuerpo = solo_desc.json()
        assert cuerpo["title"] == "Regar"
        assert cuerpo["description"] == "con manguera"
        assert cuerpo["project_id"] == pid
        assert cuerpo["state_id"] == s1

        cambia_estado = await client.patch(f"/tasks/{tid}", json={"state_id": s2})
        assert cambia_estado.status_code == 200
        assert cambia_estado.json()["state_id"] == s2
        assert (await client.get(f"/tasks/{tid}")).json()["state_id"] == s2

        vacio = await client.patch(f"/tasks/{tid}", json={})
        assert vacio.status_code == 200
        assert vacio.json()["title"] == "Regar"

        a_nulo = await client.patch(f"/tasks/{tid}", json={"description": None})
        assert a_nulo.status_code == 200
        assert a_nulo.json()["description"] is None


async def test_patch_project_id_inexistente_es_404(client: httpx.AsyncClient) -> None:
    async with client:
        pid = await _crear_proyecto(client)
        sid = await _un_state_id(client)
        tid = await _crear_tarea(client, "X", pid, sid)
        respuesta = await client.patch(f"/tasks/{tid}", json={"project_id": 9999})
    assert respuesta.status_code == 404
    assert "detail" in respuesta.json()


async def test_patch_title_invisible_es_422(client: httpx.AsyncClient) -> None:
    async with client:
        pid = await _crear_proyecto(client)
        sid = await _un_state_id(client)
        tid = await _crear_tarea(client, "X", pid, sid)
        respuesta = await client.patch(f"/tasks/{tid}", json={"title": "​"})
    assert respuesta.status_code == 422
    assert "detail" in respuesta.json()


async def test_patch_clave_desconocida_es_422(client: httpx.AsyncClient) -> None:
    async with client:
        pid = await _crear_proyecto(client)
        sid = await _un_state_id(client)
        tid = await _crear_tarea(client, "X", pid, sid)
        respuesta = await client.patch(f"/tasks/{tid}", json={"prioridad": 1})
    assert respuesta.status_code == 422
    assert "detail" in respuesta.json()


async def test_patch_task_inexistente_es_404(client: httpx.AsyncClient) -> None:
    async with client:
        respuesta = await client.patch("/tasks/9999", json={"title": "X"})
    assert respuesta.status_code == 404
    assert "detail" in respuesta.json()


async def test_delete_task_204_y_get_posterior_404(client: httpx.AsyncClient) -> None:
    async with client:
        pid = await _crear_proyecto(client)
        sid = await _un_state_id(client)
        tid = await _crear_tarea(client, "X", pid, sid)

        borrado = await client.delete(f"/tasks/{tid}")
        assert borrado.status_code == 204
        assert borrado.content == b""

        assert (await client.get(f"/tasks/{tid}")).status_code == 404


async def test_delete_task_inexistente_es_404(client: httpx.AsyncClient) -> None:
    async with client:
        respuesta = await client.delete("/tasks/9999")
    assert respuesta.status_code == 404
    assert "detail" in respuesta.json()
