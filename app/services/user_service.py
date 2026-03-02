from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User


class UserAlreadyExistsError(Exception):
    pass


class UserNotFoundError(Exception):
    pass


class UserService:
    @staticmethod
    def create_user(db: Session, email: str) -> User:
        normalized_email = email.strip().lower()
        user = User(id=str(uuid4()), email=normalized_email)
        try:
            existing = db.execute(select(User).where(User.email == normalized_email)).scalar_one_or_none()
            if existing:
                raise UserAlreadyExistsError(f"User already exists for email '{normalized_email}'")
            db.add(user)
            db.commit()
        except Exception:
            db.rollback()
            raise
        db.refresh(user)
        return user

    @staticmethod
    def get_user_by_id(db: Session, user_id: str) -> User:
        user = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
        if not user:
            raise UserNotFoundError(f"User not found for id '{user_id}'")
        return user
