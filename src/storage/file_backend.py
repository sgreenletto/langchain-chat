"""File storage backend implemented with JSON files."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from ..core.config_manager import get_config
    from ..models.schemas import Message, Preset, Session, User, UserConfig
    from .base import StorageBackend
except ImportError:
    from core.config_manager import get_config
    from models.schemas import Message, Preset, Session, User, UserConfig
    from storage.base import StorageBackend

logger = logging.getLogger(__name__)


class FileBackend(StorageBackend):
    """JSON-file implementation of the StorageBackend contract."""

    FILES = {
        "users": "users.json",
        "sessions": "sessions.json",
        "messages": "messages.json",
        "presets": "presets.json",
        "user_configs": "user_configs.json",
    }

    def __init__(self, base_path: str | Path | None = None) -> None:
        config = get_config()
        configured_path = base_path or config.storage.file.path
        path = Path(configured_path)
        if not path.is_absolute():
            path = config.project_root / path
        self.base_path = path
        self._files = {
            name: self.base_path / filename for name, filename in self.FILES.items()
        }

    async def initialize(self) -> None:
        """Create the storage directory and validate or create JSON files."""
        await asyncio.to_thread(self.base_path.mkdir, parents=True, exist_ok=True)
        for entity, path in self._files.items():
            if path.exists():
                await self._read_records(entity)
            else:
                await self._write_records(entity, [])
        logger.info(
            "File storage initialized",
            extra={"storage_type": "file", "path": str(self.base_path), "status": "ok"},
        )

    async def close(self) -> None:
        """Close storage resources.

        FileBackend opens files per operation, so there is no persistent handle
        to close.
        """
        logger.debug("File storage close completed", extra={"storage_type": "file"})

    async def save_user(self, user: User) -> User:
        """Create or update a user."""
        records = await self._read_records("users")
        self._ensure_unique_username(records, user.username, user.id)

        if user.id > 0 and self._find_record(records, user.id) is not None:
            records = [
                self._user_to_record(user) if int(record["id"]) == user.id else record
                for record in records
            ]
            await self._write_records("users", records)
            return user

        saved = user.model_copy(update={"id": self._next_id(records)})
        records.append(self._user_to_record(saved))
        await self._write_records("users", records)
        return saved

    async def get_user_by_id(self, user_id: int) -> User | None:
        """Return a user by id."""
        record = self._find_record(await self._read_records("users"), user_id)
        return self._record_to_user(record) if record else None

    async def get_user_by_username(self, username: str) -> User | None:
        """Return a user by username."""
        for record in await self._read_records("users"):
            if str(record["username"]) == username:
                return self._record_to_user(record)
        return None

    async def list_users(self) -> list[User]:
        """List all users."""
        records = sorted(
            await self._read_records("users"), key=lambda item: int(item["id"])
        )
        return [self._record_to_user(record) for record in records]

    async def delete_user(self, user_id: int) -> bool:
        """Delete a user and manually cascade related data."""
        users = await self._read_records("users")
        if self._find_record(users, user_id) is None:
            return False

        sessions = await self._read_records("sessions")
        session_ids = {
            int(session["id"])
            for session in sessions
            if int(session["user_id"]) == user_id
        }

        await self._write_records(
            "users",
            [user for user in users if int(user["id"]) != user_id],
        )
        await self._write_records(
            "sessions",
            [session for session in sessions if int(session["user_id"]) != user_id],
        )
        await self._write_records(
            "messages",
            [
                message
                for message in await self._read_records("messages")
                if int(message["session_id"]) not in session_ids
            ],
        )
        await self._write_records(
            "presets",
            [
                preset
                for preset in await self._read_records("presets")
                if preset.get("user_id") != user_id
            ],
        )
        await self._write_records(
            "user_configs",
            [
                config
                for config in await self._read_records("user_configs")
                if int(config["user_id"]) != user_id
            ],
        )
        return True

    async def save_session(self, session: Session) -> Session:
        """Create or update a session."""
        records = await self._read_records("sessions")
        if session.id > 0 and self._find_record(records, session.id) is not None:
            records = [
                self._session_to_record(session)
                if int(record["id"]) == session.id
                else record
                for record in records
            ]
            await self._write_records("sessions", records)
            return session

        saved = session.model_copy(update={"id": self._next_id(records)})
        records.append(self._session_to_record(saved))
        await self._write_records("sessions", records)
        return saved

    async def get_session(self, session_id: int) -> Session | None:
        """Return a session by id."""
        record = self._find_record(await self._read_records("sessions"), session_id)
        return self._record_to_session(record) if record else None

    async def list_sessions(self, user_id: int) -> list[Session]:
        """List sessions for a user in stable newest-first order."""
        records = [
            record
            for record in await self._read_records("sessions")
            if int(record["user_id"]) == user_id
        ]
        records.sort(
            key=lambda item: (str(item["updated_at"]), int(item["id"])), reverse=True
        )
        return [self._record_to_session(record) for record in records]

    async def delete_session(self, session_id: int) -> bool:
        """Delete a session and its messages."""
        sessions = await self._read_records("sessions")
        if self._find_record(sessions, session_id) is None:
            return False

        await self._write_records(
            "sessions",
            [session for session in sessions if int(session["id"]) != session_id],
        )
        await self._write_records(
            "messages",
            [
                message
                for message in await self._read_records("messages")
                if int(message["session_id"]) != session_id
            ],
        )
        return True

    async def save_message(self, message: Message) -> Message:
        """Create or update a message."""
        records = await self._read_records("messages")
        if message.id > 0 and self._find_record(records, message.id) is not None:
            records = [
                self._message_to_record(message)
                if int(record["id"]) == message.id
                else record
                for record in records
            ]
            await self._write_records("messages", records)
            return message

        saved = message.model_copy(update={"id": self._next_id(records)})
        records.append(self._message_to_record(saved))
        await self._write_records("messages", records)
        return saved

    async def list_messages(self, session_id: int) -> list[Message]:
        """List messages for a session in chronological order."""
        records = [
            record
            for record in await self._read_records("messages")
            if int(record["session_id"]) == session_id
        ]
        records.sort(key=lambda item: (str(item["created_at"]), int(item["id"])))
        return [self._record_to_message(record) for record in records]

    async def search_messages(
        self,
        user_id: int,
        keyword: str,
        limit: int = 20,
    ) -> list[Message]:
        """Search messages for one user without crossing user boundaries."""
        sessions = await self._read_records("sessions")
        session_ids = {
            int(session["id"])
            for session in sessions
            if int(session["user_id"]) == user_id
        }
        normalized_keyword = keyword.lower()
        matches = [
            record
            for record in await self._read_records("messages")
            if int(record["session_id"]) in session_ids
            and normalized_keyword in str(record["content"]).lower()
        ]
        matches.sort(key=lambda item: (str(item["created_at"]), int(item["id"])))
        return [self._record_to_message(record) for record in matches[:limit]]

    async def get_preset_by_id(self, preset_id: int) -> Preset | None:
        """Return any preset by id."""
        record = self._find_record(await self._read_records("presets"), preset_id)
        return self._record_to_preset(record) if record else None

    async def save_preset(self, preset: Preset) -> Preset:
        """Create or update a preset."""
        records = await self._read_records("presets")
        if not preset.id:
            saved = preset.model_copy(update={"id": self._next_id(records)})
            records.append(self._preset_to_record(saved))
            await self._write_records("presets", records)
            return saved

        if self._find_record(records, preset.id) is None:
            raise RuntimeError(f"要更新的预设不存在：id={preset.id}")

        records = [
            self._preset_to_record(preset) if int(record["id"]) == preset.id else record
            for record in records
        ]
        await self._write_records("presets", records)
        return preset

    async def get_preset(self, preset_id: int) -> Preset | None:
        """Return a preset by id."""
        return await self.get_preset_by_id(preset_id)

    async def list_presets(self, user_id: int | None = None) -> list[Preset]:
        """List built-in presets and optional user presets."""
        records = await self._read_records("presets")
        if user_id is None:
            visible = [
                record
                for record in records
                if record.get("user_id") is None or bool(record.get("is_builtin"))
            ]
        else:
            visible = [
                record
                for record in records
                if record.get("user_id") is None
                or bool(record.get("is_builtin"))
                or record.get("user_id") == user_id
            ]
        visible.sort(
            key=lambda item: (not bool(item.get("is_builtin")), int(item["id"]))
        )
        return [self._record_to_preset(record) for record in visible]

    async def delete_preset(self, preset_id: int) -> bool:
        """Delete a preset and null out references."""
        presets = await self._read_records("presets")
        if self._find_record(presets, preset_id) is None:
            return False

        await self._write_records(
            "presets",
            [preset for preset in presets if int(preset["id"]) != preset_id],
        )
        await self._write_records(
            "sessions",
            [
                {**session, "preset_id": None}
                if session.get("preset_id") == preset_id
                else session
                for session in await self._read_records("sessions")
            ],
        )
        await self._write_records(
            "users",
            [
                {**user, "default_preset_id": None}
                if user.get("default_preset_id") == preset_id
                else user
                for user in await self._read_records("users")
            ],
        )
        return True

    async def save_user_config(self, config: UserConfig) -> UserConfig:
        """Create or update one user config item."""
        records = await self._read_records("user_configs")
        existing_index = self._find_config_index(records, config.user_id, config.key)
        if config.id > 0:
            id_index = self._find_index(records, config.id)
            if id_index is not None:
                duplicate_index = self._find_config_index(
                    records,
                    config.user_id,
                    config.key,
                )
                if duplicate_index is not None and duplicate_index != id_index:
                    raise ValueError(
                        f"用户配置已存在：user_id={config.user_id}, key={config.key}"
                    )
                records[id_index] = self._user_config_to_record(config)
                await self._write_records("user_configs", records)
                return config

        if existing_index is not None:
            existing = records[existing_index]
            saved = config.model_copy(update={"id": int(existing["id"])})
            records[existing_index] = self._user_config_to_record(saved)
            await self._write_records("user_configs", records)
            return saved

        saved = config.model_copy(update={"id": self._next_id(records)})
        records.append(self._user_config_to_record(saved))
        await self._write_records("user_configs", records)
        return saved

    async def get_user_config(self, user_id: int, key: str) -> UserConfig | None:
        """Return one user config item."""
        for record in await self._read_records("user_configs"):
            if int(record["user_id"]) == user_id and str(record["key"]) == key:
                return self._record_to_user_config(record)
        return None

    async def list_user_configs(self, user_id: int) -> list[UserConfig]:
        """List config items for a user."""
        records = [
            record
            for record in await self._read_records("user_configs")
            if int(record["user_id"]) == user_id
        ]
        records.sort(key=lambda item: (str(item["key"]), int(item["id"])))
        return [self._record_to_user_config(record) for record in records]

    async def list_table_names(self) -> list[str]:
        """Return logical collection names for initialization verification."""
        return sorted(self.FILES)

    async def _read_records(self, entity: str) -> list[dict[str, Any]]:
        path = self._files[entity]
        try:
            return await asyncio.to_thread(self._read_records_sync, path)
        except Exception as exc:
            logger.exception(
                "File storage read failed",
                extra={
                    "storage_type": "file",
                    "operation": "read",
                    "path": str(path),
                    "error_type": type(exc).__name__,
                },
            )
            raise

    async def _write_records(self, entity: str, records: list[dict[str, Any]]) -> None:
        path = self._files[entity]
        try:
            await asyncio.to_thread(self._write_records_sync, path, records)
        except Exception as exc:
            logger.exception(
                "File storage write failed",
                extra={
                    "storage_type": "file",
                    "operation": "write",
                    "path": str(path),
                    "error_type": type(exc).__name__,
                },
            )
            raise

    @staticmethod
    def _read_records_sync(path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        try:
            with path.open("r", encoding="utf-8") as file:
                data = json.load(file)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"JSON 文件格式错误，未覆盖原文件：{path}") from exc
        except OSError as exc:
            raise RuntimeError(f"无法读取 JSON 文件：{path}") from exc
        if not isinstance(data, list):
            raise RuntimeError(f"JSON 文件根结构必须是列表：{path}")
        if not all(isinstance(item, dict) for item in data):
            raise RuntimeError(f"JSON 文件记录必须是对象列表：{path}")
        return data

    @staticmethod
    def _write_records_sync(path: Path, records: list[dict[str, Any]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        handle = tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        )
        temp_path = Path(handle.name)
        try:
            with handle:
                json.dump(records, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_path, path)
        except Exception:
            if temp_path.exists():
                temp_path.unlink()
            raise

    @staticmethod
    def _next_id(records: list[dict[str, Any]]) -> int:
        ids = [int(record["id"]) for record in records if "id" in record]
        return max(ids, default=0) + 1

    @staticmethod
    def _find_record(
        records: list[dict[str, Any]], record_id: int
    ) -> dict[str, Any] | None:
        for record in records:
            if int(record["id"]) == record_id:
                return record
        return None

    @staticmethod
    def _find_index(records: list[dict[str, Any]], record_id: int) -> int | None:
        for index, record in enumerate(records):
            if int(record["id"]) == record_id:
                return index
        return None

    @staticmethod
    def _find_config_index(
        records: list[dict[str, Any]],
        user_id: int,
        key: str,
    ) -> int | None:
        for index, record in enumerate(records):
            if int(record["user_id"]) == user_id and str(record["key"]) == key:
                return index
        return None

    @staticmethod
    def _ensure_unique_username(
        records: list[dict[str, Any]],
        username: str,
        user_id: int,
    ) -> None:
        for record in records:
            if str(record["username"]) == username and int(record["id"]) != user_id:
                raise ValueError(f"用户名已存在：{username}")

    @staticmethod
    def _datetime_to_iso(value: datetime) -> str:
        return value.isoformat()

    @staticmethod
    def _iso_to_datetime(value: str | datetime) -> datetime:
        if isinstance(value, datetime):
            return value
        return datetime.fromisoformat(value)

    def _user_to_record(self, user: User) -> dict[str, Any]:
        return {
            "id": user.id,
            "username": user.username,
            "default_model": user.default_model,
            "default_preset_id": user.default_preset_id,
            "created_at": self._datetime_to_iso(user.created_at),
            "updated_at": self._datetime_to_iso(user.updated_at),
        }

    def _record_to_user(self, record: dict[str, Any]) -> User:
        return User(
            id=int(record["id"]),
            username=str(record["username"]),
            default_model=record.get("default_model"),
            default_preset_id=record.get("default_preset_id"),
            created_at=self._iso_to_datetime(record["created_at"]),
            updated_at=self._iso_to_datetime(record["updated_at"]),
        )

    def _session_to_record(self, session: Session) -> dict[str, Any]:
        return {
            "id": session.id,
            "user_id": session.user_id,
            "title": session.title,
            "model_name": session.model_name,
            "preset_id": session.preset_id,
            "total_prompt_tokens": session.total_prompt_tokens,
            "total_completion_tokens": session.total_completion_tokens,
            "created_at": self._datetime_to_iso(session.created_at),
            "updated_at": self._datetime_to_iso(session.updated_at),
        }

    def _record_to_session(self, record: dict[str, Any]) -> Session:
        return Session(
            id=int(record["id"]),
            user_id=int(record["user_id"]),
            title=str(record["title"]),
            model_name=record.get("model_name"),
            preset_id=record.get("preset_id"),
            total_prompt_tokens=int(record.get("total_prompt_tokens", 0)),
            total_completion_tokens=int(record.get("total_completion_tokens", 0)),
            created_at=self._iso_to_datetime(record["created_at"]),
            updated_at=self._iso_to_datetime(record["updated_at"]),
        )

    def _message_to_record(self, message: Message) -> dict[str, Any]:
        return {
            "id": message.id,
            "session_id": message.session_id,
            "role": message.role,
            "content": message.content,
            "prompt_tokens": message.prompt_tokens,
            "completion_tokens": message.completion_tokens,
            "created_at": self._datetime_to_iso(message.created_at),
        }

    def _record_to_message(self, record: dict[str, Any]) -> Message:
        return Message(
            id=int(record["id"]),
            session_id=int(record["session_id"]),
            role=record["role"],
            content=str(record["content"]),
            prompt_tokens=int(record.get("prompt_tokens", 0)),
            completion_tokens=int(record.get("completion_tokens", 0)),
            created_at=self._iso_to_datetime(record["created_at"]),
        )

    def _preset_to_record(self, preset: Preset) -> dict[str, Any]:
        return {
            "id": preset.id,
            "user_id": preset.user_id,
            "name": preset.name,
            "description": preset.description,
            "system_prompt": preset.system_prompt,
            "is_builtin": preset.is_builtin,
            "created_at": self._datetime_to_iso(preset.created_at),
            "updated_at": self._datetime_to_iso(preset.updated_at),
        }

    def _record_to_preset(self, record: dict[str, Any]) -> Preset:
        return Preset(
            id=int(record["id"]),
            user_id=record.get("user_id"),
            name=str(record["name"]),
            description=str(record.get("description", "")),
            system_prompt=str(record["system_prompt"]),
            is_builtin=bool(record.get("is_builtin", False)),
            created_at=self._iso_to_datetime(record["created_at"]),
            updated_at=self._iso_to_datetime(record["updated_at"]),
        )

    def _user_config_to_record(self, config: UserConfig) -> dict[str, Any]:
        return {
            "id": config.id,
            "user_id": config.user_id,
            "key": config.key,
            "value": config.value,
            "updated_at": self._datetime_to_iso(config.updated_at),
        }

    def _record_to_user_config(self, record: dict[str, Any]) -> UserConfig:
        return UserConfig(
            id=int(record["id"]),
            user_id=int(record["user_id"]),
            key=str(record["key"]),
            value=str(record["value"]),
            updated_at=self._iso_to_datetime(record["updated_at"]),
        )
