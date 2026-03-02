from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import EntryType, LedgerEntry, User, Wallet


class WalletAlreadyExistsError(Exception):
    pass


class WalletNotFoundError(Exception):
    pass


class UserNotFoundError(Exception):
    pass


class InsufficientFundsError(Exception):
    pass


class WalletService:
    @staticmethod
    def _normalize_amount(amount: Decimal) -> Decimal:
        return amount.quantize(Decimal("0.01"))

    @staticmethod
    def create_wallet(db: Session, user_id: str) -> Wallet:
        try:
            user = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
            if not user:
                raise UserNotFoundError(f"User not found for id '{user_id}'")

            existing = db.execute(select(Wallet).where(Wallet.user_id == user_id)).scalar_one_or_none()
            if existing:
                raise WalletAlreadyExistsError(f"Wallet already exists for user '{user_id}'")

            wallet = Wallet(user_id=user_id, balance=Decimal("0.00"))
            db.add(wallet)
            db.commit()
        except Exception:
            db.rollback()
            raise
        db.refresh(wallet)
        return wallet

    @staticmethod
    def get_wallet_by_user_id(db: Session, user_id: str) -> Wallet:
        wallet = db.execute(select(Wallet).where(Wallet.user_id == user_id)).scalar_one_or_none()
        if not wallet:
            raise WalletNotFoundError(f"Wallet not found for user '{user_id}'")
        return wallet

    @staticmethod
    def credit(db: Session, user_id: str, amount: Decimal, reference: str | None = None) -> Wallet:
        normalized_amount = WalletService._normalize_amount(amount)
        try:
            wallet = db.execute(select(Wallet).where(Wallet.user_id == user_id).with_for_update()).scalar_one_or_none()
            if not wallet:
                raise WalletNotFoundError(f"Wallet not found for user '{user_id}'")

            wallet.balance += normalized_amount
            db.add(
                LedgerEntry(
                    wallet_id=wallet.id,
                    entry_type=EntryType.CREDIT,
                    amount=normalized_amount,
                    balance_after=wallet.balance,
                    reference=reference,
                )
            )
            db.commit()
        except Exception:
            db.rollback()
            raise
        db.refresh(wallet)
        return wallet

    @staticmethod
    def debit(db: Session, user_id: str, amount: Decimal, reference: str | None = None) -> Wallet:
        normalized_amount = WalletService._normalize_amount(amount)
        try:
            wallet = db.execute(select(Wallet).where(Wallet.user_id == user_id).with_for_update()).scalar_one_or_none()
            if not wallet:
                raise WalletNotFoundError(f"Wallet not found for user '{user_id}'")
            if wallet.balance < normalized_amount:
                raise InsufficientFundsError("Insufficient funds")

            wallet.balance -= normalized_amount
            db.add(
                LedgerEntry(
                    wallet_id=wallet.id,
                    entry_type=EntryType.DEBIT,
                    amount=normalized_amount,
                    balance_after=wallet.balance,
                    reference=reference,
                )
            )
            db.commit()
        except Exception:
            db.rollback()
            raise
        db.refresh(wallet)
        return wallet

    @staticmethod
    def get_ledger(db: Session, user_id: str, limit: int, offset: int) -> tuple[list[LedgerEntry], int]:
        wallet = WalletService.get_wallet_by_user_id(db, user_id)
        total = db.execute(select(func.count(LedgerEntry.id)).where(LedgerEntry.wallet_id == wallet.id)).scalar_one()
        items = (
            db.execute(
                select(LedgerEntry)
                .where(LedgerEntry.wallet_id == wallet.id)
                .order_by(LedgerEntry.created_at.desc(), LedgerEntry.id.desc())
                .limit(limit)
                .offset(offset)
            )
            .scalars()
            .all()
        )
        return items, total
