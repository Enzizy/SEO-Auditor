from __future__ import annotations

from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import User, WebsiteProject


def get_or_create_default_user(db: Session) -> User:
    settings = get_settings()
    user = db.scalar(select(User).where(User.email == settings.default_user_email))
    if user:
        return user
    user = User(email=settings.default_user_email, password_hash="local-dev")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_or_create_project(db: Session, website_url: str, project_label: str) -> WebsiteProject:
    user = get_or_create_default_user(db)
    domain = urlparse(str(website_url)).netloc.lower()
    project = db.scalar(
        select(WebsiteProject).where(WebsiteProject.user_id == user.id, WebsiteProject.domain == domain)
    )
    if project:
        project.label = project_label
        db.add(project)
        db.commit()
        db.refresh(project)
        return project
    project = WebsiteProject(user_id=user.id, domain=domain, label=project_label)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project

