"""Storage backend contracts and implementations."""

try:
    from .base import StorageBackend
    from .factory import StorageFactory
    from .mysql_backend import MySQLBackend
except ImportError:
    from storage.base import StorageBackend
    from storage.factory import StorageFactory
    from storage.mysql_backend import MySQLBackend

__all__ = ["MySQLBackend", "StorageBackend", "StorageFactory"]
