from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class RegisterRequest(BaseModel):
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class UpgradeRequest(BaseModel):
    plan: Literal["pro", "max"]


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    plan: str


class UserSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:         UUID
    email:      str
    plan:       str
    created_at: datetime


class ApiKeyCreatedResponse(BaseModel):
    id:      UUID
    api_key: str
    plan:    str
