"""Storage backend factory."""

try:
    from .base import StorageBackend
except ImportError:
    from storage.base import StorageBackend


class StorageFactory:
    """Create storage backends by storage type."""

    @staticmethod
    def create(storage_type: str | None = None) -> StorageBackend:
        """Return a storage backend for the requested type."""
        if storage_type is None:
            try:
                from ..core.config_manager import get_config
            except ImportError:
                from core.config_manager import get_config

            storage_type = get_config().storage.type

        normalized_type = storage_type.strip().lower()

        if normalized_type == "sqlite":
            try:
                from .sqlite_backend import SQLiteBackend
            except ImportError:
                from storage.sqlite_backend import SQLiteBackend

            return SQLiteBackend()
        if normalized_type == "mysql":
            try:
                from .mysql_backend import MySQLBackend
            except ImportError:
                from storage.mysql_backend import MySQLBackend

            return MySQLBackend()
        if normalized_type == "file":
            raise NotImplementedError("File 存储后端将在 Step 12 实现。")

        raise ValueError(f"不支持的存储后端类型：{storage_type}")
