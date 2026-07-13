"""Pydantic v2 schemas for users, sessions, messages, presets, and settings."""

from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    """Return the current UTC time for model defaults."""
    return datetime.now(timezone.utc)


class User(BaseModel):
    id: int
    username: str
    default_model: Optional[str] = None
    default_preset_id: Optional[int] = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class Session(BaseModel):
    id: int
    user_id: int
    title: str = "新会话"
    model_name: Optional[str] = None
    preset_id: Optional[int] = None
    total_prompt_tokens: int = Field(default=0, ge=0)
    total_completion_tokens: int = Field(default=0, ge=0)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class Message(BaseModel):
    id: int
    session_id: int
    role: Literal["human", "ai", "system"]
    content: str
    prompt_tokens: int = Field(default=0, ge=0)
    completion_tokens: int = Field(default=0, ge=0)
    created_at: datetime = Field(default_factory=utc_now)


class Preset(BaseModel):
    id: int
    user_id: Optional[int] = None
    name: str
    description: str = ""
    system_prompt: str
    is_builtin: bool = False
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class UserConfig(BaseModel):
    id: int
    user_id: int
    key: str
    value: str
    updated_at: datetime = Field(default_factory=utc_now)
