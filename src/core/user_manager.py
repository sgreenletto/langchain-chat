"""User management business layer."""

import logging

try:
    from ..models.schemas import User, utc_now
    from ..storage.base import StorageBackend
    from .config_manager import AppConfig, ConfigError, get_config
except ImportError:
    from core.config_manager import AppConfig, ConfigError, get_config
    from models.schemas import User, utc_now
    from storage.base import StorageBackend

logger = logging.getLogger(__name__)


class UserManager:
    """Manage users through a StorageBackend dependency."""

    def __init__(
        self,
        backend: StorageBackend,
        config: AppConfig | None = None,
    ) -> None:
        self.backend = backend
        self.config = config or get_config()

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
        saved = await self.backend.save_user(user)
        logger.info(
            "User created",
            extra={"user_id": saved.id, "operation": "create_user", "status": "ok"},
        )
        return saved

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
            logger.error(
                "User delete failed",
                extra={
                    "user_id": user.id,
                    "operation": "delete_user",
                    "status": "failed",
                },
            )
            raise ValueError(f"删除用户 '{normalized_username}' 失败。")
        logger.info(
            "User deleted",
            extra={"user_id": user.id, "operation": "delete_user", "status": "ok"},
        )
        return user

    async def update_default_model(self, user_id: int, model_alias: str) -> User:
        """Update one user's default model alias for future sessions."""
        try:
            runtime_config = self.config.validate_model_alias(
                model_alias.strip(),
                require_available=True,
            )
        except ConfigError as exc:
            raise ValueError(str(exc)) from exc
        user = await self.backend.get_user_by_id(user_id)
        if user is None:
            raise ValueError("用户不存在。")

        updated = User(
            id=user.id,
            username=user.username,
            default_model=runtime_config.alias,
            default_preset_id=user.default_preset_id,
            created_at=user.created_at,
            updated_at=utc_now(),
        )
        saved = await self.backend.save_user(updated)
        logger.info(
            "User default model updated",
            extra={
                "user_id": saved.id,
                "model": saved.default_model,
                "operation": "update_default_model",
                "status": "ok",
            },
        )
        return saved

    def get_effective_default_model(self, user: User) -> str:
        """Return a valid configured model alias for a user's next session."""
        if user.default_model:
            try:
                self.config.validate_model_alias(
                    user.default_model,
                    require_available=False,
                )
                return user.default_model
            except ConfigError:
                logger.warning(
                    "User default model is invalid; falling back to system default",
                    extra={"user_id": user.id, "model_alias": user.default_model},
                )
        return self.config.default_model_alias
