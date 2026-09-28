from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import Role


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    username: str
    display_name: str
    role: Role
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
