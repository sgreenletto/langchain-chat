"""Storage backend factory."""

import logging

try:
    from .base import StorageBackend
except ImportError:
    from storage.base import StorageBackend

logger = logging.getLogger(__name__)


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

            logger.info(
                "Storage backend selected",
                extra={"storage_type": "sqlite", "status": "creating"},
            )
            return SQLiteBackend()
        if normalized_type == "mysql":
            try:
                from .mysql_backend import MySQLBackend
            except ImportError:
                from storage.mysql_backend import MySQLBackend

            logger.info(
                "Storage backend selected",
                extra={"storage_type": "mysql", "status": "creating"},
            )
            return MySQLBackend()
        if normalized_type == "file":
            try:
                from .file_backend import FileBackend
            except ImportError:
                from storage.file_backend import FileBackend

            logger.info(
                "Storage backend selected",
                extra={"storage_type": "file", "status": "creating"},
            )
            return FileBackend()

        logger.error(
            "Unsupported storage backend type",
            extra={"storage_type": storage_type, "status": "invalid"},
        )
        raise ValueError(f"不支持的存储后端类型：{storage_type}")
