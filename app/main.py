from typing import Annotated

from fastapi import Depends, FastAPI
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import State
from app.schemas import StateOut

app = FastAPI(title="TaskFlow", version="0.1.0")

SessionDep = Annotated[Session, Depends(get_session)]


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/states", response_model=list[StateOut])
def list_states(session: SessionDep) -> list[State]:
    """Catálogo de estados, ordenado por el campo de orden y ``id`` de desempate."""

    stmt = select(State).order_by(State.sort_order, State.id)
    return list(session.scalars(stmt).all())
