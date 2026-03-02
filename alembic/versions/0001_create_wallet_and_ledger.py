"""create wallet and ledger

Revision ID: 0001_create_wallet_and_ledger
Revises: 
Create Date: 2026-03-02 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0001_create_wallet_and_ledger"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    entry_type = sa.Enum("credit", "debit", name="entry_type")

    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.create_table(
        "wallets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("balance", sa.Numeric(precision=18, scale=2), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index(op.f("ix_wallets_id"), "wallets", ["id"], unique=False)
    op.create_index(op.f("ix_wallets_user_id"), "wallets", ["user_id"], unique=True)

    op.create_table(
        "ledger_entries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("wallet_id", sa.Integer(), nullable=False),
        sa.Column("entry_type", entry_type, nullable=False),
        sa.Column("amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("balance_after", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("reference", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["wallet_id"], ["wallets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ledger_entries_id"), "ledger_entries", ["id"], unique=False)
    op.create_index(op.f("ix_ledger_entries_wallet_id"), "ledger_entries", ["wallet_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_ledger_entries_wallet_id"), table_name="ledger_entries")
    op.drop_index(op.f("ix_ledger_entries_id"), table_name="ledger_entries")
    op.drop_table("ledger_entries")

    op.drop_index(op.f("ix_wallets_user_id"), table_name="wallets")
    op.drop_index(op.f("ix_wallets_id"), table_name="wallets")
    op.drop_table("wallets")

    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_index(op.f("ix_users_id"), table_name="users")
    op.drop_table("users")

    sa.Enum(name="entry_type").drop(op.get_bind(), checkfirst=True)
