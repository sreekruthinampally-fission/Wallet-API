from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.ledger_entry import EntryType


class LedgerEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    wallet_id: int
    entry_type: EntryType
    amount: Decimal
    balance_after: Decimal
    reference: str | None
    created_at: datetime


class LedgerListResponse(BaseModel):
    items: list[LedgerEntryResponse]
    total: int
    limit: int
    offset: int
