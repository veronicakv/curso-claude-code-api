"""Rutas del recurso Tareas (v1).

`due_at` y `GET /tasks?overdue=true` llegan con Tareas v2; aquí no existen.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Project, State, Task
from app.schemas import TaskIn, TaskOut

router = APIRouter()

SessionDep = Annotated[Session, Depends(get_session)]


def _validar_referencias(session: Session, project_id: int, state_id: int) -> None:
    """`404` si el proyecto o el estado referenciados no existen."""
    if session.get(Project, project_id) is None:
        raise HTTPException(status_code=404, detail="proyecto no encontrado")
    if session.get(State, state_id) is None:
        raise HTTPException(status_code=404, detail="estado no encontrado")


@router.post("/tasks", status_code=201, response_model=TaskOut)
def create_task(payload: TaskIn, session: SessionDep) -> Task:
    _validar_referencias(session, payload.project_id, payload.state_id)
    task = Task(
        title=payload.title,
        description=payload.description,
        project_id=payload.project_id,
        state_id=payload.state_id,
    )
    session.add(task)
    session.commit()
    session.refresh(task)
    return task


@router.get("/tasks/{task_id}", response_model=TaskOut)
def get_task(task_id: int, session: SessionDep) -> Task:
    task = session.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="tarea no encontrada")
    return task
