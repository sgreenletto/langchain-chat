"""Focused tests for the Step 12 FileBackend."""

import asyncio

import pytest
from src.models.schemas import Message, Preset, Session, User, UserConfig
from src.storage.file_backend import FileBackend


def run(coro):
    return asyncio.run(coro)


async def exercise_file_backend(tmp_path):
    backend = FileBackend(tmp_path)
    await backend.initialize()
    try:
        assert {
            "users.json",
            "sessions.json",
            "messages.json",
            "presets.json",
            "user_configs.json",
        } == {path.name for path in tmp_path.iterdir()}

        alice = await backend.save_user(User(id=0, username="alice"))
        bob = await backend.save_user(User(id=0, username="bob"))
        with pytest.raises(ValueError, match="用户名已存在"):
            await backend.save_user(User(id=0, username="alice"))

        preset = await backend.save_preset(
            Preset(
                id=0,
                user_id=alice.id,
                name="custom",
                system_prompt="short test prompt",
            )
        )
        assert [item.id for item in await backend.list_presets(alice.id)] == [preset.id]
        assert await backend.list_presets(bob.id) == []

        session = await backend.save_session(
            Session(
                id=0,
                user_id=alice.id,
                title="file session",
                model_name="default",
                preset_id=preset.id,
            )
        )
        human = await backend.save_message(
            Message(id=0, session_id=session.id, role="human", content="needle")
        )
        ai = await backend.save_message(
            Message(id=0, session_id=session.id, role="ai", content="needle reply")
        )
        assert [item.id for item in await backend.list_messages(session.id)] == [
            human.id,
            ai.id,
        ]
        assert len(await backend.search_messages(alice.id, "needle")) == 2
        assert await backend.search_messages(bob.id, "needle") == []

        saved_config = await backend.save_user_config(
            UserConfig(id=0, user_id=alice.id, key="theme", value="dark")
        )
        assert saved_config.value == "dark"
        updated_config = await backend.save_user_config(
            UserConfig(id=0, user_id=alice.id, key="theme", value="light")
        )
        assert updated_config.id == saved_config.id
        assert (await backend.get_user_config(alice.id, "theme")).value == "light"

        assert await backend.delete_session(session.id) is True
        assert await backend.list_messages(session.id) == []

        session = await backend.save_session(
            Session(id=0, user_id=alice.id, title="cascade", preset_id=preset.id)
        )
        await backend.save_message(
            Message(id=0, session_id=session.id, role="human", content="cascade")
        )
        assert await backend.delete_user(alice.id) is True
        assert await backend.get_session(session.id) is None
        assert await backend.get_preset_by_id(preset.id) is None
        assert await backend.get_user_config(alice.id, "theme") is None
    finally:
        await backend.close()

    restored = FileBackend(tmp_path)
    await restored.initialize()
    try:
        assert (await restored.get_user_by_username("bob")).id == bob.id
    finally:
        await restored.close()


def test_file_backend_crud_cascade_and_restore(tmp_path):
    run(exercise_file_backend(tmp_path))
