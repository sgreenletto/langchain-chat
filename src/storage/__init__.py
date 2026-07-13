"""Storage backend contracts and implementations."""

from storage.base import StorageBackend
from storage.factory import StorageFactory

__all__ = ["StorageBackend", "StorageFactory"]
