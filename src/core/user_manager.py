"""User management business layer."""

from models.schemas import User
from storage.base import StorageBackend


class UserManager:
    """Manage users through a StorageBackend dependency."""

    def __init__(self, backend: StorageBackend) -> None:
        self.backend = backend

    async def create_user(
        self,
        username: str,
        default_model: str | None = None,
    ) -> User:
        """Create a user after validating business rules."""
        normalized_username = username.strip()
        if not normalized_username:
            raise ValueError("用户名不能为空。")

        existing_user = await self.backend.get_user_by_username(normalized_username)
        if existing_user is not None:
            raise ValueError(f"用户名 '{normalized_username}' 已存在。")

        user = User(
            id=0,
            username=normalized_username,
            default_model=default_model,
        )
        return await self.backend.save_user(user)

    async def get_user(self, username: str) -> User | None:
        """Return a user by username, or None if it does not exist."""
        normalized_username = username.strip()
        if not normalized_username:
            return None
        return await self.backend.get_user_by_username(normalized_username)

    async def get_user_by_id(self, user_id: int) -> User | None:
        """Return a user by id, or None if it does not exist."""
        return await self.backend.get_user_by_id(user_id)

    async def list_users(self) -> list[User]:
        """List all users."""
        return await self.backend.list_users()

    async def delete_user(self, username: str) -> User:
        """Delete a user by username."""
        normalized_username = username.strip()
        if not normalized_username:
            raise ValueError("用户名不能为空。")

        user = await self.backend.get_user_by_username(normalized_username)
        if user is None:
            raise ValueError(f"用户 '{normalized_username}' 不存在。")

        deleted = await self.backend.delete_user(user.id)
        if not deleted:
            raise ValueError(f"删除用户 '{normalized_username}' 失败。")
        return user
