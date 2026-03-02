from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.ledger import LedgerListResponse
from app.schemas.wallet import AmountRequest, BalanceResponse, WalletResponse
from app.services.wallet_service import (
    InsufficientFundsError,
    UserNotFoundError,
    WalletAlreadyExistsError,
    WalletNotFoundError,
    WalletService,
)

router = APIRouter(prefix="/wallets", tags=["wallets"])


@router.post("/{user_id}", response_model=WalletResponse, status_code=status.HTTP_201_CREATED)
def create_wallet(
    user_id: str = Path(
        ...,
        min_length=36,
        max_length=36,
        description="Unique user identifier returned by POST /users",
        examples=["11111111-2222-3333-4444-555555555555"],
    ),
    db: Session = Depends(get_db),
) -> WalletResponse:
    try:
        wallet = WalletService.create_wallet(db, user_id)
        return wallet
    except UserNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except WalletAlreadyExistsError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post("/{user_id}/credit", response_model=WalletResponse)
def credit_wallet(
    user_id: str = Path(
        ...,
        min_length=36,
        max_length=36,
        description="Wallet owner user identifier returned by POST /users",
        examples=["11111111-2222-3333-4444-555555555555"],
    ),
    payload: AmountRequest = Body(...),
    db: Session = Depends(get_db),
) -> WalletResponse:
    try:
        wallet = WalletService.credit(db, user_id, payload.amount, payload.reference)
        return wallet
    except WalletNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/{user_id}/debit", response_model=WalletResponse)
def debit_wallet(
    user_id: str = Path(
        ...,
        min_length=36,
        max_length=36,
        description="Wallet owner user identifier returned by POST /users",
        examples=["11111111-2222-3333-4444-555555555555"],
    ),
    payload: AmountRequest = Body(...),
    db: Session = Depends(get_db),
) -> WalletResponse:
    try:
        wallet = WalletService.debit(db, user_id, payload.amount, payload.reference)
        return wallet
    except WalletNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InsufficientFundsError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get("/{user_id}/balance", response_model=BalanceResponse)
def get_wallet_balance(
    user_id: str = Path(
        ...,
        min_length=36,
        max_length=36,
        description="Wallet owner user identifier returned by POST /users",
        examples=["11111111-2222-3333-4444-555555555555"],
    ),
    db: Session = Depends(get_db),
) -> BalanceResponse:
    try:
        wallet = WalletService.get_wallet_by_user_id(db, user_id)
        return BalanceResponse(user_id=wallet.user_id, balance=wallet.balance)
    except WalletNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/{user_id}/ledger", response_model=LedgerListResponse)
def get_wallet_ledger(
    user_id: str = Path(
        ...,
        min_length=36,
        max_length=36,
        description="Wallet owner user identifier returned by POST /users",
        examples=["11111111-2222-3333-4444-555555555555"],
    ),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> LedgerListResponse:
    try:
        items, total = WalletService.get_ledger(db, user_id=user_id, limit=limit, offset=offset)
        return LedgerListResponse(items=items, total=total, limit=limit, offset=offset)
    except WalletNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
