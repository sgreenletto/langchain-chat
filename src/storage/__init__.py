"""Storage backend contracts and implementations."""

try:
    from .base import StorageBackend
    from .factory import StorageFactory
except ImportError:
    from storage.base import StorageBackend
    from storage.factory import StorageFactory

__all__ = ["StorageBackend", "StorageFactory"]
