"""Rutas del recurso Proyectos.

`DELETE /projects/{id}` responde `204` sin tareas, `409` si las tiene y `404`
si no existe. La FK `tasks.project_id ON DELETE RESTRICT` es la red de
seguridad; el `409` legible lo da una consulta previa.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Project, Task
from app.schemas import ProjectIn, ProjectOut, ProjectPatch

router = APIRouter()

SessionDep = Annotated[Session, Depends(get_session)]


@router.post("/projects", status_code=201, response_model=ProjectOut)
def create_project(payload: ProjectIn, session: SessionDep) -> Project:
    project = Project(name=payload.name, description=payload.description)
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


@router.get("/projects", response_model=list[ProjectOut])
def list_projects(session: SessionDep) -> list[Project]:
    """Proyectos ordenados por ``id`` ascendente."""
    stmt = select(Project).order_by(Project.id)
    return list(session.scalars(stmt).all())


@router.get("/projects/{project_id}", response_model=ProjectOut)
def get_project(project_id: int, session: SessionDep) -> Project:
    project = session.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="proyecto no encontrado")
    return project


@router.patch("/projects/{project_id}", response_model=ProjectOut)
def update_project(project_id: int, patch: ProjectPatch, session: SessionDep) -> Project:
    project = session.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="proyecto no encontrado")

    campos = patch.model_fields_set
    if "name" in campos:
        if patch.name is None:
            raise HTTPException(status_code=422, detail="name no puede ser nulo")
        project.name = patch.name
    if "description" in campos:
        project.description = patch.description

    session.commit()
    session.refresh(project)
    return project


@router.delete("/projects/{project_id}", status_code=204)
def delete_project(project_id: int, session: SessionDep) -> None:
    """`204` si no tiene tareas, `409` si las tiene, `404` si no existe."""
    project = session.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="proyecto no encontrado")
    tiene_tareas = session.scalar(
        select(Task.id).where(Task.project_id == project_id).limit(1)
    )
    if tiene_tareas is not None:
        raise HTTPException(status_code=409, detail="el proyecto tiene tareas")
    session.delete(project)
    session.commit()
