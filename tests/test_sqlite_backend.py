"""Tests for the Step 3 SQLite storage backend."""

import asyncio
import sys
from pathlib import Path

import pytest

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from models.schemas import Message, Preset, Session, User, UserConfig  # noqa: E402
from storage.sqlite_backend import SQLiteBackend  # noqa: E402


def run(coro):
    """Run an async storage operation in tests without pytest-asyncio."""
    return asyncio.run(coro)


async def exercise_backend(db_path):
    backend = SQLiteBackend(db_path)
    await backend.initialize()
    try:
        user = await backend.save_user(User(id=0, username="alice"))
        assert user.id > 0
        assert (await backend.get_user_by_username("alice")).id == user.id

        preset = await backend.save_preset(
            Preset(
                id=0,
                user_id=user.id,
                name="测试预设",
                system_prompt="用于测试",
            )
        )
        session = await backend.save_session(
            Session(
                id=0,
                user_id=user.id,
                title="测试会话",
                model_name="example-chat-model",
                preset_id=preset.id,
            )
        )
        await backend.save_message(
            Message(id=0, session_id=session.id, role="human", content="hello")
        )
        await backend.save_message(
            Message(id=0, session_id=session.id, role="ai", content="hello back")
        )

        messages = await backend.list_messages(session.id)
        assert [message.role for message in messages] == ["human", "ai"]
        assert len(await backend.search_messages(user.id, "hello")) == 2

        config = await backend.save_user_config(
            UserConfig(id=0, user_id=user.id, key="theme", value="default")
        )
        assert config.id > 0
        assert (await backend.get_user_config(user.id, "theme")).value == "default"

        assert await backend.delete_user(user.id) is True
        assert await backend.get_session(session.id) is None
        assert await backend.list_messages(session.id) == []
        assert await backend.get_preset(preset.id) is None
        assert await backend.get_user_config(user.id, "theme") is None
    finally:
        await backend.close()


def test_sqlite_backend_crud_and_cascade(tmp_path):
    run(exercise_backend(tmp_path / "app.db"))


def test_sqlite_backend_requires_initialize(tmp_path):
    backend = SQLiteBackend(tmp_path / "app.db")
    with pytest.raises(RuntimeError, match="尚未初始化"):
        run(backend.list_users())
