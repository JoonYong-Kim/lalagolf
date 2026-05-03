import uuid
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class UserProfileResponse(BaseModel):
    bio: str | None
    home_course: str | None
    handicap_target: Decimal | None
    privacy_default: str
    share_course_by_default: bool
    share_exact_date_by_default: bool

    model_config = ConfigDict(from_attributes=True)


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str
    role: str
    profile: UserProfileResponse | None

    model_config = ConfigDict(from_attributes=True)


class RegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=256)
    display_name: str = Field(min_length=1, max_length=120)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        email = value.strip().lower()
        if "@" not in email:
            raise ValueError("Invalid email")
        return email

    @field_validator("display_name")
    @classmethod
    def normalize_display_name(cls, value: str) -> str:
        return value.strip()


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=256)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class ProfileUpdateRequest(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    bio: str | None = Field(default=None, max_length=1000)
    home_course: str | None = Field(default=None, max_length=200)
    handicap_target: Decimal | None = None
    privacy_default: str | None = None
    share_course_by_default: bool | None = None
    share_exact_date_by_default: bool | None = None

    @field_validator("privacy_default")
    @classmethod
    def validate_privacy_default(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if value not in {"private", "link_only", "public", "followers"}:
            raise ValueError("Invalid privacy_default")
        return value


class AuthEnvelope(BaseModel):
    data: dict[str, UserResponse]
