"""Initialize the SQLite database and run a Step 3 smoke test."""

import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from models.schemas import Message, Preset, Session, User, UserConfig  # noqa: E402
from storage.factory import StorageFactory  # noqa: E402
from storage.sqlite_backend import SQLiteBackend  # noqa: E402

EXPECTED_TABLES = {"users", "sessions", "messages", "presets", "user_configs"}
SMOKE_USERNAME = "smoke_test_user"


async def run_init_and_smoke_test() -> None:
    """Create tables and verify the SQLite backend with a small data flow."""
    print("=" * 60)
    print("Step 3：SQLite 存储后端初始化与冒烟测试")
    print("=" * 60)

    backend = StorageFactory.create("sqlite")
    if not isinstance(backend, SQLiteBackend):
        raise RuntimeError("StorageFactory 未返回 SQLiteBackend。")

    print("[1/8] 创建存储后端: SQLiteBackend")

    try:
        await backend.initialize()
        tables = set(await backend.list_table_names())
        missing_tables = EXPECTED_TABLES - tables
        if missing_tables:
            raise RuntimeError(f"数据库缺少表：{sorted(missing_tables)}")

        print(f"[2/8] 数据库已初始化: {backend.db_path}")
        print(f"      五张表: {', '.join(sorted(tables))}")

        existing_user = await backend.get_user_by_username(SMOKE_USERNAME)
        if existing_user is not None:
            await backend.delete_user(existing_user.id)
            print(f"      [清理] 删除残留测试用户 id={existing_user.id}")

        user = await backend.save_user(User(id=0, username=SMOKE_USERNAME))
        found_user = await backend.get_user_by_username(SMOKE_USERNAME)
        if found_user is None or found_user.id != user.id:
            raise RuntimeError("按用户名查询测试用户失败。")
        print(f"[3/8] 创建并查询用户: id={user.id}, username={user.username}")

        preset = await backend.save_preset(
            Preset(
                id=0,
                user_id=user.id,
                name="冒烟测试预设",
                description="Step 3 冒烟测试使用",
                system_prompt="你正在执行 SQLite 存储层冒烟测试。",
            )
        )

        session = await backend.save_session(
            Session(
                id=0,
                user_id=user.id,
                title="冒烟测试会话",
                model_name="example-chat-model",
                preset_id=preset.id,
            )
        )
        print(f"[4/8] 创建会话: id={session.id}, title={session.title}")

        human_message = await backend.save_message(
            Message(
                id=0,
                session_id=session.id,
                role="human",
                content="你好，这是冒烟测试",
                prompt_tokens=4,
            )
        )
        ai_message = await backend.save_message(
            Message(
                id=0,
                session_id=session.id,
                role="ai",
                content="你好，冒烟测试通过",
                completion_tokens=5,
            )
        )
        print(f"[5/8] 保存消息: human id={human_message.id}, ai id={ai_message.id}")

        messages = await backend.list_messages(session.id)
        search_hits = await backend.search_messages(user.id, "冒烟")
        if len(messages) != 2 or len(search_hits) != 2:
            raise RuntimeError("消息列表或搜索结果数量不符合预期。")
        print(f"[6/8] 查询消息: 会话 {session.id} 共 {len(messages)} 条")
        print(f"      搜索 '冒烟': 命中 {len(search_hits)} 条")

        saved_config = await backend.save_user_config(
            UserConfig(id=0, user_id=user.id, key="theme", value="default")
        )
        loaded_config = await backend.get_user_config(user.id, "theme")
        if loaded_config is None or loaded_config.value != saved_config.value:
            raise RuntimeError("用户配置保存或读取失败。")
        print(f"[7/8] 保存并读取用户配置: {loaded_config.key}={loaded_config.value}")

        deleted = await backend.delete_user(user.id)
        deleted_session = await backend.get_session(session.id)
        orphan_messages = await backend.list_messages(session.id)
        orphan_config = await backend.get_user_config(user.id, "theme")
        orphan_preset = await backend.get_preset(preset.id)
        if (
            not deleted
            or deleted_session is not None
            or orphan_messages
            or orphan_config is not None
            or orphan_preset is not None
        ):
            raise RuntimeError("级联删除验证失败。")
        print("[8/8] 删除用户并验证会话、消息、预设、配置已级联清理")

        print("[完成] 数据库初始化与冒烟测试全部通过")
    finally:
        await backend.close()


def main() -> None:
    """Run script with a non-zero exit code on failure."""
    try:
        asyncio.run(run_init_and_smoke_test())
    except Exception as exc:
        print(f"[失败] {exc}")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
