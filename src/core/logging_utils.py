"""Logging helpers for structured JSONL application logs."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any


class JsonLineFormatter(logging.Formatter):
    """Format each LogRecord as one standalone JSON object."""

    CONTEXT_FIELDS = (
        "user_id",
        "session_id",
        "model",
        "model_alias",
        "status",
        "error_type",
        "storage_type",
        "operation",
        "path",
        "call_type",
        "timeout",
        "max_retries",
    )

    SENSITIVE_MARKERS = (
        "api_key",
        "authorization",
        "password",
        "token",
        "secret",
        "connection_string",
    )

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": self._redact(record.getMessage()),
        }

        for field in self.CONTEXT_FIELDS:
            if hasattr(record, field):
                payload[field] = self._redact(getattr(record, field))

        if record.exc_info:
            payload["exception"] = self._redact(self.formatException(record.exc_info))

        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

    @classmethod
    def _redact(cls, value: Any) -> Any:
        if isinstance(value, dict):
            return {key: cls._redact_by_key(key, item) for key, item in value.items()}
        if isinstance(value, list | tuple):
            return [cls._redact(item) for item in value]
        if isinstance(value, str):
            lowered = value.lower()
            if any(marker in lowered for marker in cls.SENSITIVE_MARKERS):
                return "[REDACTED]"
        return value

    @classmethod
    def _redact_by_key(cls, key: str, value: Any) -> Any:
        lowered = key.lower()
        if any(marker in lowered for marker in cls.SENSITIVE_MARKERS):
            return "[REDACTED]"
        return cls._redact(value)
