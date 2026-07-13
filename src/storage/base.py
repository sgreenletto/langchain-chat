"""Abstract storage backend interface for future persistence implementations."""

from abc import ABC, abstractmethod
from typing import Optional

from models.schemas import Message, Preset, Session, User, UserConfig


class StorageBackend(ABC):
    """Async contract implemented by concrete storage backends in later steps."""

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the storage backend."""

    @abstractmethod
    async def close(self) -> None:
        """Close storage resources."""

    @abstractmethod
    async def save_user(self, user: User) -> User:
        """Create or update a user."""

    @abstractmethod
    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Return a user by id."""

    @abstractmethod
    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Return a user by username."""

    @abstractmethod
    async def list_users(self) -> list[User]:
        """List all users."""

    @abstractmethod
    async def delete_user(self, user_id: int) -> bool:
        """Delete a user."""

    @abstractmethod
    async def save_session(self, session: Session) -> Session:
        """Create or update a session."""

    @abstractmethod
    async def get_session(self, session_id: int) -> Optional[Session]:
        """Return a session by id."""

    @abstractmethod
    async def list_sessions(self, user_id: int) -> list[Session]:
        """List sessions for a user."""

    @abstractmethod
    async def delete_session(self, session_id: int) -> bool:
        """Delete a session."""

    @abstractmethod
    async def save_message(self, message: Message) -> Message:
        """Create or update a message."""

    @abstractmethod
    async def list_messages(self, session_id: int) -> list[Message]:
        """List messages for a session."""

    @abstractmethod
    async def search_messages(
        self,
        user_id: int,
        keyword: str,
        limit: int = 20,
    ) -> list[Message]:
        """Search messages for a user."""

    @abstractmethod
    async def save_preset(self, preset: Preset) -> Preset:
        """Create or update a preset."""

    @abstractmethod
    async def get_preset(self, preset_id: int) -> Optional[Preset]:
        """Return a preset by id."""

    @abstractmethod
    async def list_presets(self, user_id: Optional[int] = None) -> list[Preset]:
        """List built-in and user presets."""

    @abstractmethod
    async def delete_preset(self, preset_id: int) -> bool:
        """Delete a preset."""

    @abstractmethod
    async def save_user_config(self, config: UserConfig) -> UserConfig:
        """Create or update one user config item."""

    @abstractmethod
    async def get_user_config(self, user_id: int, key: str) -> Optional[UserConfig]:
        """Return one user config item."""

    @abstractmethod
    async def list_user_configs(self, user_id: int) -> list[UserConfig]:
        """List config items for a user."""
