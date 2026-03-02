from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import (
    AmountRequest,
    BalanceResponse,
    LedgerListResponse,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
    WalletResponse,
)
from app.services import (
    InsufficientFundsError,
    InvalidCredentialsError,
    UserAlreadyExistsError,
    UserNotFoundError,
    UserService,
    WalletAlreadyExistsError,
    WalletNotFoundError,
    WalletService,
    create_access_token,
    decode_access_token,
)

router = APIRouter()
security = HTTPBearer(auto_error=False)
AUTH_RESPONSES = {
    401: {"description": "Unauthorized"},
}


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
):
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing authorization token")
    try:
        payload = decode_access_token(credentials.credentials)
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token") from exc

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
    try:
        return UserService.get_user_by_id(db, user_id)
    except UserNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User from token no longer exists") from exc


@router.post(
    "/auth/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["auth"],
    responses={409: {"description": "Conflict"}},
)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> UserResponse:
    try:
        return UserService.create_user(db, payload.email, payload.password)
    except UserAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post(
    "/auth/login",
    response_model=TokenResponse,
    tags=["auth"],
    responses={401: {"description": "Unauthorized"}},
)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    try:
        user = UserService.authenticate_user(db, payload.email, payload.password)
        token, expires_in = create_access_token(user.id, user.email)
        return TokenResponse(access_token=token, expires_in=expires_in)
    except InvalidCredentialsError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


@router.post(
    "/wallets",
    response_model=WalletResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["wallets"],
    responses={**AUTH_RESPONSES, 404: {"description": "Not Found"}, 409: {"description": "Conflict"}},
)
def create_wallet(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> WalletResponse:
    try:
        return WalletService.create_wallet(db, current_user.id)
    except UserNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except WalletAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post(
    "/wallets/credit",
    response_model=WalletResponse,
    tags=["wallets"],
    responses={**AUTH_RESPONSES, 404: {"description": "Not Found"}, 422: {"description": "Validation failed"}},
)
def credit_wallet(
    payload: AmountRequest = Body(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> WalletResponse:
    try:
        return WalletService.credit(db, current_user.id, payload.amount, payload.reference)
    except WalletNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/wallets/debit",
    response_model=WalletResponse,
    tags=["wallets"],
    responses={
        **AUTH_RESPONSES,
        404: {"description": "Not Found"},
        409: {"description": "Conflict"},
        422: {"description": "Validation failed"},
    },
)
def debit_wallet(
    payload: AmountRequest = Body(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> WalletResponse:
    try:
        return WalletService.debit(db, current_user.id, payload.amount, payload.reference)
    except WalletNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InsufficientFundsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get(
    "/wallets/balance",
    response_model=BalanceResponse,
    tags=["wallets"],
    responses={**AUTH_RESPONSES, 404: {"description": "Not Found"}},
)
def get_wallet_balance(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> BalanceResponse:
    try:
        wallet = WalletService.get_wallet_by_user_id(db, current_user.id)
        return BalanceResponse(user_id=wallet.user_id, balance=wallet.balance)
    except WalletNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get(
    "/wallets/ledger",
    response_model=LedgerListResponse,
    tags=["wallets"],
    responses={**AUTH_RESPONSES, 404: {"description": "Not Found"}, 422: {"description": "Validation failed"}},
)
def get_wallet_ledger(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> LedgerListResponse:
    try:
        items, total = WalletService.get_ledger(db, user_id=current_user.id, limit=limit, offset=offset)
        return LedgerListResponse(items=items, total=total, limit=limit, offset=offset)
    except WalletNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
