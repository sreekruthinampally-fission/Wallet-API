from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CreateUserRequest(BaseModel):
    email: str = Field(min_length=5, max_length=255, examples=["alice@example.com"])

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        email = value.strip().lower()
        if "@" not in email or email.count("@") != 1:
            raise ValueError("Invalid email format")
        local, domain = email.split("@")
        if not local or "." not in domain or domain.startswith(".") or domain.endswith("."):
            raise ValueError("Invalid email format")
        return email


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    created_at: datetime
