from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.user import CreateUserRequest, UserResponse
from app.services.user_service import UserAlreadyExistsError, UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(payload: CreateUserRequest, db: Session = Depends(get_db)) -> UserResponse:
    try:
        return UserService.create_user(db, payload.email)
    except UserAlreadyExistsError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
