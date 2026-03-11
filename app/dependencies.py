from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db import get_session


DbSession = Session


def get_db(session: Session = Depends(get_session)) -> Session:
    return session

