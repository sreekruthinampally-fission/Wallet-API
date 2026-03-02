from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_timeout=settings.db_pool_timeout,
    pool_recycle=settings.db_pool_recycle,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    # Import models before create_all so metadata is fully registered.
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    inspector = inspect(engine)
    if "users" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("users")}
        if "password_hash" not in columns:
            with engine.begin() as connection:
                connection.execute(
                    text("ALTER TABLE users ADD COLUMN password_hash VARCHAR(255) NOT NULL DEFAULT ''")
                )
    # Add important constraints/indexes for existing databases created before hardening.
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1
                        FROM pg_constraint
                        WHERE conname = 'ck_wallets_balance_non_negative'
                    ) THEN
                        ALTER TABLE wallets
                        ADD CONSTRAINT ck_wallets_balance_non_negative CHECK (balance >= 0);
                    END IF;
                END $$;
                """
            )
        )
        connection.execute(
            text(
                """
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1
                        FROM pg_constraint
                        WHERE conname = 'ck_ledger_entries_amount_positive'
                    ) THEN
                        ALTER TABLE ledger_entries
                        ADD CONSTRAINT ck_ledger_entries_amount_positive CHECK (amount > 0);
                    END IF;
                END $$;
                """
            )
        )
        connection.execute(
            text(
                """
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1
                        FROM pg_constraint
                        WHERE conname = 'ck_ledger_entries_balance_after_non_negative'
                    ) THEN
                        ALTER TABLE ledger_entries
                        ADD CONSTRAINT ck_ledger_entries_balance_after_non_negative CHECK (balance_after >= 0);
                    END IF;
                END $$;
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_ledger_entries_wallet_id_created_at
                ON ledger_entries(wallet_id, created_at DESC, id DESC);
                """
            )
        )
