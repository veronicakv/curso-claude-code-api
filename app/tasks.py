"""Rutas del recurso Tareas (v2).

Incluye ``due_at`` (opcional, normalizado a UTC), ``priority`` (entero opcional
1..3) y el filtro ``GET /tasks?overdue=true``.
"""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Project, State, Task
from app.schemas import ErrorDetail, TaskIn, TaskOut, TaskPatch

router = APIRouter()

SessionDep = Annotated[Session, Depends(get_session)]

_NOT_FOUND = {
    404: {"model": ErrorDetail, "description": "Tarea, proyecto o estado no encontrado"}
}


def _validar_referencias(session: Session, project_id: int, state_id: int) -> None:
    """`404` si el proyecto o el estado referenciados no existen."""
    if session.get(Project, project_id) is None:
        raise HTTPException(status_code=404, detail="proyecto no encontrado")
    if session.get(State, state_id) is None:
        raise HTTPException(status_code=404, detail="estado no encontrado")


@router.post("/tasks", status_code=201, response_model=TaskOut, responses=_NOT_FOUND)
def create_task(payload: TaskIn, session: SessionDep) -> Task:
    _validar_referencias(session, payload.project_id, payload.state_id)
    task = Task(
        title=payload.title,
        description=payload.description,
        project_id=payload.project_id,
        state_id=payload.state_id,
        due_at=payload.due_at,
        priority=payload.priority,
    )
    session.add(task)
    session.commit()
    session.refresh(task)
    return task


@router.get("/tasks", response_model=list[TaskOut])
def list_tasks(
    session: SessionDep,
    project_id: int | None = None,
    state_id: int | None = None,
    overdue: bool | None = None,
) -> list[Task]:
    """Tareas ordenadas por ``id`` ascendente.

    ``project_id`` y ``state_id`` filtran, solos o combinados (AND). Filtrar por
    un id inexistente devuelve lista vacía, no ``404``.

    ``overdue=true`` deja solo las tareas con ``due_at`` anterior al instante de
    evaluación y estado distinto de ``HECHA``. Una tarea sin ``due_at`` nunca
    está vencida. ``overdue=false`` no filtra.
    """
    stmt = select(Task).order_by(Task.id)
    if project_id is not None:
        stmt = stmt.where(Task.project_id == project_id)
    if state_id is not None:
        stmt = stmt.where(Task.state_id == state_id)
    if overdue:
        hecha_ids = select(State.id).where(State.code == "HECHA").scalar_subquery()
        stmt = stmt.where(
            Task.due_at.is_not(None),
            Task.due_at < datetime.now(UTC),
            Task.state_id.not_in(hecha_ids),
        )
    return list(session.scalars(stmt).all())


@router.get("/tasks/{task_id}", response_model=TaskOut, responses=_NOT_FOUND)
def get_task(task_id: int, session: SessionDep) -> Task:
    task = session.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="tarea no encontrada")
    return task


@router.patch("/tasks/{task_id}", response_model=TaskOut, responses=_NOT_FOUND)
def update_task(task_id: int, patch: TaskPatch, session: SessionDep) -> Task:
    task = session.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="tarea no encontrada")

    campos = patch.model_fields_set
    if "title" in campos:
        if patch.title is None:
            raise HTTPException(status_code=422, detail="title no puede ser nulo")
        task.title = patch.title
    if "description" in campos:
        task.description = patch.description
    if "project_id" in campos:
        if patch.project_id is None:
            raise HTTPException(status_code=422, detail="project_id no puede ser nulo")
        if session.get(Project, patch.project_id) is None:
            raise HTTPException(status_code=404, detail="proyecto no encontrado")
        task.project_id = patch.project_id
    if "state_id" in campos:
        if patch.state_id is None:
            raise HTTPException(status_code=422, detail="state_id no puede ser nulo")
        if session.get(State, patch.state_id) is None:
            raise HTTPException(status_code=404, detail="estado no encontrado")
        task.state_id = patch.state_id
    if "due_at" in campos:
        task.due_at = patch.due_at
    if "priority" in campos:
        task.priority = patch.priority

    session.commit()
    session.refresh(task)
    return task


@router.delete("/tasks/{task_id}", status_code=204, responses=_NOT_FOUND)
def delete_task(task_id: int, session: SessionDep) -> None:
    task = session.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="tarea no encontrada")
    session.delete(task)
    session.commit()
