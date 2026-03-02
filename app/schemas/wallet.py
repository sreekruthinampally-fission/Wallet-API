from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AmountRequest(BaseModel):
    amount: Decimal = Field(gt=0, examples=["100.00"])
    reference: str | None = Field(default=None, max_length=128, examples=["salary-credit"])

    @field_validator("amount")
    @classmethod
    def validate_amount_precision(cls, value: Decimal) -> Decimal:
        if value.as_tuple().exponent < -2:
            raise ValueError("Amount supports at most 2 decimal places")
        return value.quantize(Decimal("0.01"))

    @field_validator("reference")
    @classmethod
    def normalize_reference(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


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
