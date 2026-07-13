"""Tests for the Step 7 SessionManager business layer."""

import asyncio
import sys
from pathlib import Path

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from core.session_manager import SessionManager  # noqa: E402
from models.schemas import Preset, User  # noqa: E402
from storage.sqlite_backend import SQLiteBackend  # noqa: E402


def run(coro):
    return asyncio.run(coro)


async def exercise_session_manager(db_path):
    backend = SQLiteBackend(db_path)
    await backend.initialize()
    manager = SessionManager(backend, title_max_length=10)
    try:
        alice = await backend.save_user(User(id=0, username="alice"))
        bob = await backend.save_user(User(id=0, username="bob"))
        preset = await backend.save_preset(
            Preset(
                id=0,
                user_id=alice.id,
                name="alice preset",
                system_prompt="你是 Alice 的助手。",
            )
        )

        session = await manager.create_session(
            user_id=alice.id,
            model_name="example-chat-model",
            preset_id=preset.id,
        )
        await manager.save_user_message(session, "你好")
        _, session = await manager.save_ai_message_and_update_session(
            session,
            "你好，我在。",
            prompt_tokens=7,
            completion_tokens=5,
        )

        assert session.total_prompt_tokens == 7
        assert session.total_completion_tokens == 5

        messages = await manager.load_langchain_messages(session)
        assert isinstance(messages[0], SystemMessage)
        assert isinstance(messages[1], HumanMessage)
        assert isinstance(messages[2], AIMessage)
        assert sum(isinstance(message, SystemMessage) for message in messages) == 1

        assert await manager.get_user_session(alice.id, session.id) is not None
        assert await manager.get_user_session(bob.id, session.id) is None

        title = await manager.generate_session_title(
            "  这是一个很长的标题内容用于测试兜底逻辑  "
        )
        assert title == "这是一个很长的标题内容用于测试兜底逻辑"

        updated = await manager.rename_session(alice.id, session.id, "新标题")
        assert updated.title == "新标题"

        with pytest.raises(ValueError, match="不能为空"):
            await manager.rename_session(alice.id, session.id, "   ")
        with pytest.raises(ValueError, match="不能超过"):
            await manager.rename_session(
                alice.id,
                session.id,
                "这是一个超过长度限制的标题",
            )
        with pytest.raises(ValueError, match="不属于当前用户"):
            await manager.rename_session(bob.id, session.id, "坏标题")

        deleted = await manager.delete_session(alice.id, session.id)
        assert deleted.id == session.id
        assert await backend.get_session(session.id) is None
        assert await backend.list_messages(session.id) == []
        with pytest.raises(ValueError, match="不属于当前用户"):
            await manager.get_session(alice.id, session.id)
    finally:
        await backend.close()


def test_session_manager_flow_and_isolation(tmp_path):
    run(exercise_session_manager(tmp_path / "app.db"))
