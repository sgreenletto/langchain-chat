"""Tests for the Step 7 SessionManager business layer."""

import asyncio
import sys
from pathlib import Path

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from core.config_manager import AppConfig, EnvSettings  # noqa: E402
from core.session_manager import SessionManager  # noqa: E402
from core.user_manager import UserManager  # noqa: E402
from models.schemas import Preset, User  # noqa: E402
from storage.sqlite_backend import SQLiteBackend  # noqa: E402


def run(coro):
    return asyncio.run(coro)


def make_test_config(tmp_path: Path) -> AppConfig:
    return AppConfig(
        app={
            "name": "langchain-chat",
            "version": "0.1.0",
            "current_step": "Step 10  导出与模型切换",
        },
        llm={
            "default_model": "default",
            "available_models": [
                {
                    "alias": "default",
                    "display_name": "默认模型",
                    "model": "test-default-model",
                    "api_base_url_env": "API_BASE_URL",
                    "api_key_env": "API_KEY",
                },
                {
                    "alias": "backup",
                    "display_name": "备用模型",
                    "model": "test-backup-model",
                    "api_base_url_env": "API_BASE_URL",
                    "api_key_env": "API_KEY",
                },
                {
                    "alias": "missing",
                    "display_name": "缺失模型",
                    "model": "test-missing-model",
                    "api_base_url_env": "MISSING_API_BASE_URL",
                    "api_key_env": "MISSING_API_KEY",
                },
            ],
            "temperature": 0.7,
            "max_tokens": 1024,
            "timeout": 10,
            "max_retries": 1,
        },
        storage={
            "type": "sqlite",
            "sqlite": {"database_path": "unused.db"},
            "mysql": {
                "host_env": "MYSQL_HOST",
                "port_env": "MYSQL_PORT",
                "user_env": "MYSQL_USER",
                "password_env": "MYSQL_PASSWORD",
                "database_env": "MYSQL_DATABASE",
            },
            "file": {"base_dir": "data/users", "encoding": "utf-8"},
        },
        conversation={"title_max_length": 10},
        export={
            "dir": "data/users/{username}/exports",
            "filename_template": "{conversation_id}_{timestamp}.{format}",
        },
        env=EnvSettings(
            api_base_url="https://unit.test/v1",
            api_key="unit-test-key",
            model_name="test-default-model",
        ),
        project_root=tmp_path,
    )


async def exercise_session_manager(db_path):
    config = make_test_config(db_path.parent)
    backend = SQLiteBackend(db_path)
    await backend.initialize()
    manager = SessionManager(backend, title_max_length=10, config=config)
    user_manager = UserManager(backend, config=config)
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
        session = await manager.rename_session(alice.id, session.id, "Python 测试")
        await manager.save_user_message(session, "你好")
        await manager.save_user_message(session, "search target 中文关键词")
        _, session = await manager.save_ai_message_and_update_session(
            session,
            "hello search reply",
            prompt_tokens=7,
            completion_tokens=5,
        )

        assert session.total_prompt_tokens == 7
        assert session.total_completion_tokens == 5

        messages = await manager.load_langchain_messages(session)
        assert isinstance(messages[0], SystemMessage)
        assert isinstance(messages[1], HumanMessage)
        assert isinstance(messages[3], AIMessage)
        assert sum(isinstance(message, SystemMessage) for message in messages) == 1
        stored_messages = await manager.get_session_messages(alice.id, session.id)
        assert [message.role for message in stored_messages] == ["human", "human", "ai"]
        assert await manager.search_messages(alice.id, "   ") == []
        chinese_results = await manager.search_messages(alice.id, "中文关键词")
        assert len(chinese_results) == 1
        english_results = await manager.search_messages(alice.id, "search")
        assert len(english_results) == 2
        assert await manager.search_messages(bob.id, "search") == []

        assert await manager.get_user_session(alice.id, session.id) is not None
        assert await manager.get_user_session(bob.id, session.id) is None

        exported = await manager.export_session_markdown(alice, session.id)
        assert exported.parent == (
            db_path.parent / "data" / "users" / "alice" / "exports"
        )
        assert "Python_测试" in exported.name
        exported_text = exported.read_text(encoding="utf-8")
        assert "# Python 测试" in exported_text
        assert "- 用户：alice" in exported_text
        assert "- 预设：alice preset" in exported_text
        assert "## 消息记录" in exported_text
        assert "search target 中文关键词" in exported_text
        exported_again = await manager.export_session_markdown(alice, session.id)
        assert exported_again != exported
        with pytest.raises(ValueError, match="不属于当前用户"):
            await manager.export_session_markdown(bob, session.id)

        switched = await manager.update_session_model(alice.id, session.id, "backup")
        assert switched.model_name == "backup"
        assert len(await manager.get_session_messages(alice.id, session.id)) == 3
        with pytest.raises(ValueError, match="缺少必要环境变量"):
            await manager.update_session_model(alice.id, session.id, "missing")
        assert (await manager.get_session(alice.id, session.id)).model_name == "backup"

        updated_user = await user_manager.update_default_model(alice.id, "backup")
        assert updated_user.default_model == "backup"
        next_session = await manager.create_session(
            user_id=alice.id,
            model_name=user_manager.get_effective_default_model(updated_user),
        )
        assert next_session.model_name == "backup"

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
        with pytest.raises(ValueError, match="不属于当前用户"):
            await manager.get_session_messages(alice.id, session.id)
    finally:
        await backend.close()


def test_session_manager_flow_and_isolation(tmp_path):
    run(exercise_session_manager(tmp_path / "app.db"))
