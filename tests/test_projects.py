"""Pruebas del recurso Proyectos contra PostgreSQL real.

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
    """Cliente ASGI con la sesión de BD apuntando a la base de test migrada.

    Crea ``taskflow_test`` si no existe, la deja limpia y en ``head`` (lo que
    también siembra el catálogo de estados) y sobreescribe la dependencia de
    sesión de la app. No toca la base principal.
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


# --- Incremento 2: POST /projects, GET /projects y GET /projects/{id} --------


async def test_post_crea_y_get_lista_en_orden(client: httpx.AsyncClient) -> None:
    async with client:
        creado = await client.post("/projects", json={"name": "Casa"})
        assert creado.status_code == 201
        cuerpo = creado.json()
        assert set(cuerpo.keys()) == {"id", "name", "description"}
        assert isinstance(cuerpo["id"], int) and cuerpo["id"] > 0
        assert cuerpo["name"] == "Casa"
        assert cuerpo["description"] is None

        await client.post("/projects", json={"name": "Trabajo", "description": "oficina"})
        await client.post("/projects", json={"name": "Huerto"})

        listado = await client.get("/projects")
        assert listado.status_code == 200
        items = listado.json()
        assert [p["name"] for p in items] == ["Casa", "Trabajo", "Huerto"]
        assert [p["id"] for p in items] == sorted(p["id"] for p in items)
        for p in items:
            assert set(p.keys()) == {"id", "name", "description"}


async def test_get_projects_es_lista_en_la_raiz(client: httpx.AsyncClient) -> None:
    async with client:
        respuesta = await client.get("/projects")
    assert respuesta.status_code == 200
    assert isinstance(respuesta.json(), list)


async def test_get_por_id_devuelve_esquema_exacto(client: httpx.AsyncClient) -> None:
    async with client:
        creado = (await client.post("/projects", json={"name": "Casa"})).json()
        obtenido = await client.get(f"/projects/{creado['id']}")
    assert obtenido.status_code == 200
    assert set(obtenido.json().keys()) == {"id", "name", "description"}


async def test_get_por_id_inexistente_es_404(client: httpx.AsyncClient) -> None:
    async with client:
        respuesta = await client.get("/projects/9999")
    assert respuesta.status_code == 404
    assert "detail" in respuesta.json()


async def test_get_projects_id_no_entero_es_422(client: httpx.AsyncClient) -> None:
    async with client:
        respuesta = await client.get("/projects/abc")
    assert respuesta.status_code == 422


@pytest.mark.parametrize("name", ["   ", "​"])
async def test_post_rechaza_name_vacio_o_invisible(
    client: httpx.AsyncClient, name: str
) -> None:
    async with client:
        respuesta = await client.post("/projects", json={"name": name})
    assert respuesta.status_code == 422
    assert "detail" in respuesta.json()


async def test_post_con_clave_desconocida_es_422(client: httpx.AsyncClient) -> None:
    async with client:
        respuesta = await client.post("/projects", json={"name": "Casa", "color": "rojo"})
    assert respuesta.status_code == 422
    assert "detail" in respuesta.json()


async def test_post_sin_name_es_422(client: httpx.AsyncClient) -> None:
    async with client:
        respuesta = await client.post("/projects", json={"description": "sin nombre"})
    assert respuesta.status_code == 422
    assert "detail" in respuesta.json()


# --- Incremento 3: PATCH /projects/{id} -------------------------------------


async def test_patch_parcial(client: httpx.AsyncClient) -> None:
    async with client:
        pid = (await client.post("/projects", json={"name": "Casa"})).json()["id"]

        con_desc = await client.patch(f"/projects/{pid}", json={"description": "reforma"})
        assert con_desc.status_code == 200
        assert con_desc.json()["name"] == "Casa"
        assert con_desc.json()["description"] == "reforma"

        a_nulo = await client.patch(f"/projects/{pid}", json={"description": None})
        assert a_nulo.status_code == 200
        assert a_nulo.json()["description"] is None

        vacio = await client.patch(f"/projects/{pid}", json={})
        assert vacio.status_code == 200
        assert vacio.json()["name"] == "Casa"


async def test_patch_name_valido_cambia_el_nombre(client: httpx.AsyncClient) -> None:
    async with client:
        pid = (await client.post("/projects", json={"name": "Casa"})).json()["id"]

        parcheado = await client.patch(f"/projects/{pid}", json={"name": "Otro"})
        assert parcheado.status_code == 200
        assert set(parcheado.json().keys()) == {"id", "name", "description"}
        assert parcheado.json()["name"] == "Otro"

        assert (await client.get(f"/projects/{pid}")).json()["name"] == "Otro"


async def test_patch_name_invisible_es_422(client: httpx.AsyncClient) -> None:
    async with client:
        pid = (await client.post("/projects", json={"name": "Casa"})).json()["id"]
        respuesta = await client.patch(f"/projects/{pid}", json={"name": "​"})
    assert respuesta.status_code == 422
    assert "detail" in respuesta.json()


async def test_patch_id_inexistente_es_404(client: httpx.AsyncClient) -> None:
    async with client:
        respuesta = await client.patch("/projects/9999", json={"name": "X"})
    assert respuesta.status_code == 404
    assert "detail" in respuesta.json()


async def test_patch_con_clave_desconocida_es_422(client: httpx.AsyncClient) -> None:
    async with client:
        pid = (await client.post("/projects", json={"name": "Casa"})).json()["id"]
        respuesta = await client.patch(f"/projects/{pid}", json={"nope": 1})
    assert respuesta.status_code == 422
    assert "detail" in respuesta.json()

