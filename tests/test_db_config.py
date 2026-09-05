import pytest


def test_database_url_se_construye_desde_el_entorno(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("POSTGRES_USER", "taskflow")
    monkeypatch.setenv("POSTGRES_PASSWORD", "taskflow_local_dev")
    monkeypatch.setenv("POSTGRES_DB", "taskflow")
    monkeypatch.setenv("POSTGRES_PORT", "5432")

    from app.db import build_database_url

    url = build_database_url()

    assert url == "postgresql+psycopg://taskflow:taskflow_local_dev@localhost:5432/taskflow"


def test_database_url_es_dialecto_psycopg(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("POSTGRES_USER", "u")
    monkeypatch.setenv("POSTGRES_PASSWORD", "p")
    monkeypatch.setenv("POSTGRES_DB", "d")
    monkeypatch.setenv("POSTGRES_PORT", "6543")

    from app.db import build_database_url

    assert build_database_url().startswith("postgresql+psycopg://")
