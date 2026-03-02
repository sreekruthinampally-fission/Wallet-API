from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class AmountRequest(BaseModel):
    amount: Decimal = Field(gt=0, examples=["100.00"])
    reference: str | None = Field(default=None, max_length=128, examples=["salary-credit"])


class WalletResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: str
    balance: Decimal
    created_at: datetime
    updated_at: datetime


class BalanceResponse(BaseModel):
    user_id: str
    balance: Decimal
