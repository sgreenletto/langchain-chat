"""Optional integration tests for MySQLBackend."""

import asyncio
import os
import sys
import uuid
from pathlib import Path

import aiomysql
import pytest
from src.core.config_manager import AppConfig, EnvSettings
from src.models.schemas import Message, Preset, Session, User, UserConfig
from src.storage.mysql_backend import MySQLBackend

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from core.preset_manager import PresetManager  # noqa: E402

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_MYSQL_TESTS") != "1",
    reason="MySQL 集成测试需要设置 RUN_MYSQL_TESTS=1",
)


def run(coro):
    return asyncio.run(coro)


async def fetch_user_with_independent_connection(
    config: AppConfig,
    *,
    user_id: int | None = None,
    username: str | None = None,
) -> dict | None:
    mysql = config.get_mysql_config(require_available=True)
    connection = await aiomysql.connect(
        host=mysql.host,
        port=mysql.port,
        user=mysql.user,
        password=mysql.password,
        db=mysql.database,
        charset="utf8mb4",
        autocommit=True,
        cursorclass=aiomysql.DictCursor,
    )
    try:
        async with connection.cursor() as cursor:
            if user_id is not None:
                await cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            elif username is not None:
                await cursor.execute(
                    "SELECT * FROM users WHERE username = %s",
                    (username,),
                )
            else:
                raise ValueError("user_id or username is required")
            return await cursor.fetchone()
    finally:
        connection.close()


def make_mysql_test_config(
    tmp_path: Path,
    *,
    pool_min_size: int = 1,
    pool_max_size: int = 2,
) -> AppConfig:
    database = os.getenv("MYSQL_TEST_DATABASE", "")
    if not database:
        pytest.fail("启用 MySQL 测试时必须设置 MYSQL_TEST_DATABASE。")
    if "test" not in database.lower():
        pytest.fail("MYSQL_TEST_DATABASE 名称必须包含 test，避免误用正式库。")

    return AppConfig(
        app={
            "name": "langchain-chat",
            "version": "0.1.0",
            "current_step": "Step 11  MySQL 存储后端",
        },
        llm={
            "default_model": "default",
            "available_models": [
                {
                    "alias": "default",
                    "display_name": "默认模型",
                    "model": "test-model",
                }
            ],
            "temperature": 0.7,
            "max_tokens": 1024,
            "timeout": 10,
            "max_retries": 1,
        },
        storage={
            "type": "mysql",
            "sqlite": {"database_path": "unused.db"},
            "mysql": {
                "host_env": "MYSQL_HOST",
                "port_env": "MYSQL_PORT",
                "user_env": "MYSQL_USER",
                "password_env": "MYSQL_PASSWORD",
                "database_env": "MYSQL_TEST_DATABASE",
                "pool_min_size": pool_min_size,
                "pool_max_size": pool_max_size,
            },
            "file": {"base_dir": "data/users", "encoding": "utf-8"},
        },
        conversation={"title_max_length": 50},
        export={
            "dir": "data/users/{username}/exports",
            "filename_template": "{conversation_id}_{timestamp}.{format}",
        },
        env=EnvSettings(
            mysql_host=os.getenv("MYSQL_HOST", "localhost"),
            mysql_port=int(os.getenv("MYSQL_PORT", "3306")),
            mysql_user=os.getenv("MYSQL_USER", "root"),
            mysql_password=os.getenv("MYSQL_PASSWORD", ""),
            mysql_database=database,
        ),
        project_root=tmp_path,
        app_env="test",
    )


async def exercise_mysql_backend(tmp_path: Path) -> None:
    config = make_mysql_test_config(tmp_path)
    backend = MySQLBackend(config)
    username = f"mysql_test_{uuid.uuid4().hex}"
    other_username = f"mysql_other_{uuid.uuid4().hex}"
    builtin_name = f"mysql_builtin_{uuid.uuid4().hex}"
    manager_builtin_name = f"mysql_manager_builtin_{uuid.uuid4().hex}"
    builtin_yaml = tmp_path / "mysql_builtin_presets.yaml"
    builtin_ids: list[int] = []
    await backend.initialize()
    try:
        tables = set(await backend.list_table_names())
        assert {"users", "sessions", "messages", "presets", "user_configs"} <= tables

        user = await backend.save_user(User(id=0, username=username))
        other_user = await backend.save_user(User(id=0, username=other_username))
        assert (await backend.get_user_by_username(username)).id == user.id
        assert any(item.id == user.id for item in await backend.list_users())

        builtin = await backend.save_preset(
            Preset(
                id=0,
                user_id=None,
                name=builtin_name,
                description="builtin integration",
                system_prompt="You are a MySQL built-in preset.",
                is_builtin=True,
            )
        )
        builtin_ids.append(builtin.id)
        assert builtin.id > 0
        loaded_builtin = await backend.get_preset_by_id(builtin.id)
        assert loaded_builtin is not None
        assert loaded_builtin.user_id is None
        assert loaded_builtin.name == builtin_name
        assert loaded_builtin.is_builtin is True
        assert any(
            item.id == builtin.id for item in await backend.list_presets(user_id=None)
        )

        updated_user = await backend.save_user(
            User(
                id=user.id,
                username=username,
                default_model="default",
                default_preset_id=None,
                created_at=user.created_at,
            )
        )
        assert updated_user.default_model == "default"

        preset = await backend.save_preset(
            Preset(
                id=0,
                user_id=user.id,
                name="mysql preset",
                description="integration",
                system_prompt="你是 MySQL 测试助手。",
            )
        )
        assert (await backend.get_preset_by_id(preset.id)).name == "mysql preset"
        assert any(item.id == preset.id for item in await backend.list_presets(user.id))
        other_presets = await backend.list_presets(other_user.id)
        assert all(item.user_id != user.id for item in other_presets)

        updated_preset = await backend.save_preset(
            Preset(
                id=preset.id,
                user_id=user.id,
                name="mysql preset updated",
                description="integration updated",
                system_prompt="Updated MySQL preset.",
                is_builtin=False,
                created_at=preset.created_at,
            )
        )
        assert updated_preset.id == preset.id
        assert updated_preset.name == "mysql preset updated"

        builtin_yaml.write_text(
            f"""
presets:
  - name: {manager_builtin_name}
    description: system preset
    system_prompt: You are a MySQL built-in preset.
""",
            encoding="utf-8",
        )
        preset_manager = PresetManager(backend, builtin_yaml)
        assert await preset_manager.load_builtin_presets() == 1
        assert await preset_manager.load_builtin_presets() == 0
        after_builtin_ids = {
            item.id
            for item in await backend.list_presets(user_id=None)
            if item.is_builtin and item.name == manager_builtin_name
        }
        builtin_ids.extend(after_builtin_ids)
        assert len(after_builtin_ids) == 1

        session = await backend.save_session(
            Session(
                id=0,
                user_id=user.id,
                title="mysql session",
                model_name="default",
                preset_id=preset.id,
            )
        )
        assert (await backend.get_session(session.id)).title == "mysql session"
        session_ids = [item.id for item in await backend.list_sessions(user.id)]
        assert session_ids == [session.id]
        assert await backend.list_sessions(other_user.id) == []

        human = await backend.save_message(
            Message(
                id=0,
                session_id=session.id,
                role="human",
                content="mysql search keyword",
                prompt_tokens=3,
            )
        )
        ai = await backend.save_message(
            Message(
                id=0,
                session_id=session.id,
                role="ai",
                content="mysql response keyword",
                completion_tokens=5,
            )
        )
        assert [item.id for item in await backend.list_messages(session.id)] == [
            human.id,
            ai.id,
        ]
        assert len(await backend.search_messages(user.id, "keyword")) == 2
        assert await backend.search_messages(other_user.id, "keyword") == []

        saved_config = await backend.save_user_config(
            UserConfig(id=0, user_id=user.id, key="theme", value="dark")
        )
        assert saved_config.value == "dark"
        updated_config = await backend.save_user_config(
            UserConfig(id=0, user_id=user.id, key="theme", value="light")
        )
        assert updated_config.value == "light"
        assert len(await backend.list_user_configs(user.id)) == 1

        assert await backend.delete_session(session.id) is True
        assert await backend.get_session(session.id) is None
        assert await backend.list_messages(session.id) == []

        session = await backend.save_session(
            Session(id=0, user_id=user.id, title="cascade", preset_id=preset.id)
        )
        await backend.save_message(
            Message(id=0, session_id=session.id, role="human", content="cascade")
        )
        assert await backend.delete_user(user.id) is True
        assert await backend.get_session(session.id) is None
        assert await backend.list_messages(session.id) == []
        assert await backend.get_preset_by_id(preset.id) is None
        assert await backend.get_user_config(user.id, "theme") is None
    finally:
        remaining = await backend.get_user_by_username(username)
        if remaining is not None:
            await backend.delete_user(remaining.id)
        other_remaining = await backend.get_user_by_username(other_username)
        if other_remaining is not None:
            await backend.delete_user(other_remaining.id)
        for builtin_id in builtin_ids:
            await backend.delete_preset(builtin_id)
        await backend.close()


async def exercise_mysql_multiconnection_user_save(tmp_path: Path) -> None:
    config = make_mysql_test_config(tmp_path, pool_min_size=2, pool_max_size=2)
    backend: MySQLBackend | None = MySQLBackend(config)
    username = f"mysql_pool_user_{uuid.uuid4().hex}"
    second_username = f"mysql_pool_user_{uuid.uuid4().hex}"
    await backend.initialize()
    try:
        user = await backend.save_user(User(id=0, username=username))
        assert user.id > 0

        direct_by_id = await fetch_user_with_independent_connection(
            config,
            user_id=user.id,
        )
        assert direct_by_id is not None
        assert direct_by_id["username"] == username

        direct_by_username = await fetch_user_with_independent_connection(
            config,
            username=username,
        )
        assert direct_by_username is not None
        assert int(direct_by_username["id"]) == user.id

        await backend.close()
        backend = MySQLBackend(config)
        await backend.initialize()
        restored = await backend.get_user_by_id(user.id)
        assert restored is not None
        assert restored.username == username

        second_user = await backend.save_user(User(id=0, username=second_username))
        assert second_user.id > 0
        assert second_user.id != user.id

        with pytest.raises(aiomysql.IntegrityError):
            await backend.save_user(User(id=0, username=username))
        assert (await backend.get_user_by_username(username)).id == user.id

        session = await backend.save_session(
            Session(id=0, user_id=user.id, title="mysql pool session")
        )
        assert session.id > 0
        assert session.user_id == user.id
    finally:
        if backend is not None:
            for item_username in (username, second_username):
                remaining = await backend.get_user_by_username(item_username)
                if remaining is not None:
                    await backend.delete_user(remaining.id)
            await backend.close()


def test_mysql_backend_integration(tmp_path):
    run(exercise_mysql_backend(tmp_path))


def test_mysql_save_user_multiconnection_regression(tmp_path):
    run(exercise_mysql_multiconnection_user_save(tmp_path))
