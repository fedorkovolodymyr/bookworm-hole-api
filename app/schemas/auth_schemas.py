from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr


class RegisterSchema(BaseModel):
    email: EmailStr
    username: str
    password: str
    display_name: str


class LoginSchema(BaseModel):
    email: EmailStr
    password: str


class RefreshRequestSchema(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    username: str
    display_name: str
    is_active: bool
    is_admin: bool


class RegisterResponse(BaseModel):
    user: UserResponse
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
