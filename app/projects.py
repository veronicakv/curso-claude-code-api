"""Rutas del recurso Proyectos."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Project
from app.schemas import ProjectIn, ProjectOut

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
