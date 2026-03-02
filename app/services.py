from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import hmac
import secrets
from uuid import uuid4

from jose import JWTError, jwt
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import EntryType, LedgerEntry, User, Wallet


class UserAlreadyExistsError(Exception):
    pass


class UserNotFoundError(Exception):
    pass


class WalletAlreadyExistsError(Exception):
    pass


class WalletNotFoundError(Exception):
    pass


class InsufficientFundsError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        settings.password_hash_iterations,
    )
    return f"pbkdf2_sha256${settings.password_hash_iterations}${salt}${digest.hex()}"


def verify_password(plain_password: str, password_hash: str) -> bool:
    try:
        parts = password_hash.split("$")
        if len(parts) == 3:
            # Backward compatibility for legacy hashes: pbkdf2_sha256$salt$hash
            scheme, salt, stored_hash = parts
            iterations = 120_000
        elif len(parts) == 4:
            scheme, iterations_raw, salt, stored_hash = parts
            iterations = int(iterations_raw)
        else:
            return False
        if scheme != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            plain_password.encode("utf-8"),
            salt.encode("utf-8"),
            iterations,
        ).hex()
        return hmac.compare_digest(digest, stored_hash)
    except Exception:
        return False


def create_access_token(user_id: str, email: str) -> tuple[str, int]:
    expires_in = settings.jwt_access_token_expire_minutes * 60
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    payload = {"sub": user_id, "email": email, "exp": expires_at}
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token, expires_in


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])


class UserService:
    @staticmethod
    def create_user(db: Session, email: str, password: str) -> User:
        normalized_email = email.strip().lower()
        user = User(id=str(uuid4()), email=normalized_email, password_hash=hash_password(password))
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
    def authenticate_user(db: Session, email: str, password: str) -> User:
        normalized_email = email.strip().lower()
        user = db.execute(select(User).where(User.email == normalized_email)).scalar_one_or_none()
        if not user or not verify_password(password, user.password_hash):
            raise InvalidCredentialsError("Invalid email or password")
        return user

    @staticmethod
    def get_user_by_id(db: Session, user_id: str) -> User:
        user = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
        if not user:
            raise UserNotFoundError(f"User not found for id '{user_id}'")
        return user


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
