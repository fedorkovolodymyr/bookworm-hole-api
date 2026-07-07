from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.user import Locale
from app.schemas.collection_schemas import CollectionResponse
from app.schemas.common_schemas import Page


class UpdateUserSchema(BaseModel):
    display_name: str | None = None
    bio: str | None = None
    avatar_url: str | None = None
    locale: Locale | None = None
    timezone: str | None = None


class ChangePasswordSchema(BaseModel):
    current_password: str
    new_password: str


class UserProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    username: str
    display_name: str
    bio: str | None
    avatar_url: str | None
    locale: str
    timezone: str
    is_active: bool
    is_admin: bool


class PublicUserProfileResponse(BaseModel):
    username: str
    display_name: str
    bio: str | None
    avatar_url: str | None
    collections: Page[CollectionResponse]


class AdminUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    username: str
    display_name: str
    is_active: bool
    is_admin: bool


class PasswordResetTokenResponse(BaseModel):
    reset_token: str
