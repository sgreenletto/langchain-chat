"""StorageBackend contract tests for SQLiteBackend and FileBackend."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable

import pytest
from src.models.schemas import Message, Preset, Session, User, UserConfig
from src.storage.file_backend import FileBackend
from src.storage.sqlite_backend import SQLiteBackend

pytestmark = pytest.mark.asyncio


async def test_initialize_close_and_empty_results(
    storage_backend: SQLiteBackend | FileBackend,
) -> None:
    assert await storage_backend.list_users() == []
    assert await storage_backend.get_user_by_id(404) is None
    assert await storage_backend.get_user_by_username("missing") is None
    assert await storage_backend.get_session(404) is None
    assert await storage_backend.list_sessions(404) == []
    assert await storage_backend.list_messages(404) == []
    assert await storage_backend.search_messages(404, "needle") == []
    assert await storage_backend.get_preset_by_id(404) is None
    assert await storage_backend.get_user_config(404, "theme") is None
    assert await storage_backend.list_user_configs(404) == []


async def test_user_crud_and_unique_username(
    storage_backend: SQLiteBackend | FileBackend,
    make_user: Callable[..., User],
) -> None:
    alice = await storage_backend.save_user(make_user("alice"))
    bob = await storage_backend.save_user(make_user("bob"))

    assert alice.id > 0
    assert bob.id > alice.id
    assert (await storage_backend.get_user_by_id(alice.id)).username == "alice"
    assert (await storage_backend.get_user_by_username("bob")).id == bob.id
    assert [user.username for user in await storage_backend.list_users()] == [
        "alice",
        "bob",
    ]

    updated = await storage_backend.save_user(
        make_user(
            "alice-renamed",
            user_id=alice.id,
            default_model="backup",
            default_preset_id=None,
        )
    )
    assert updated.id == alice.id
    assert updated.username == "alice-renamed"
    assert updated.default_model == "backup"
    assert await storage_backend.get_user_by_username("alice") is None

    with pytest.raises((ValueError, sqlite3.IntegrityError)):
        await storage_backend.save_user(make_user("bob"))


async def test_sessions_messages_order_and_isolated_search(
    storage_backend: SQLiteBackend | FileBackend,
    make_user: Callable[..., User],
    make_session: Callable[..., Session],
    make_message: Callable[..., Message],
) -> None:
    alice = await storage_backend.save_user(make_user("alice"))
    bob = await storage_backend.save_user(make_user("bob"))
    first = await storage_backend.save_session(
        make_session(alice.id, title="first", model_name="default")
    )
    second = await storage_backend.save_session(
        make_session(alice.id, title="second", model_name="backup")
    )
    other = await storage_backend.save_session(
        make_session(bob.id, title="other", model_name="default")
    )

    assert (await storage_backend.get_session(first.id)).title == "first"
    alice_sessions = await storage_backend.list_sessions(alice.id)
    assert [session.id for session in alice_sessions] == [second.id, first.id]
    assert await storage_backend.list_sessions(9999) == []

    renamed = await storage_backend.save_session(
        Session(
            id=first.id,
            user_id=alice.id,
            title="renamed",
            model_name="backup",
            preset_id=first.preset_id,
            total_prompt_tokens=first.total_prompt_tokens,
            total_completion_tokens=first.total_completion_tokens,
            created_at=first.created_at,
            updated_at=first.updated_at,
        )
    )
    assert renamed.title == "renamed"
    assert renamed.model_name == "backup"

    system = await storage_backend.save_message(
        make_message(first.id, role="system", content="system")
    )
    human = await storage_backend.save_message(
        make_message(first.id, role="human", content="needle one")
    )
    ai = await storage_backend.save_message(
        make_message(first.id, role="ai", content="needle two")
    )
    await storage_backend.save_message(
        make_message(other.id, role="human", content="needle other user")
    )

    messages = await storage_backend.list_messages(first.id)
    assert [message.id for message in messages] == [system.id, human.id, ai.id]
    assert [message.role for message in messages] == ["system", "human", "ai"]

    search_results = await storage_backend.search_messages(alice.id, "needle")
    assert [message.id for message in search_results] == [human.id, ai.id]
    assert await storage_backend.search_messages(bob.id, "one") == []
    assert len(await storage_backend.search_messages(alice.id, "needle", limit=1)) == 1


async def test_preset_visibility_update_and_delete(
    storage_backend: SQLiteBackend | FileBackend,
    make_user: Callable[..., User],
    make_preset: Callable[..., Preset],
) -> None:
    alice = await storage_backend.save_user(make_user("alice"))
    bob = await storage_backend.save_user(make_user("bob"))
    builtin = await storage_backend.save_preset(
        make_preset(name="builtin", is_builtin=True)
    )
    alice_private = await storage_backend.save_preset(
        make_preset(user_id=alice.id, name="alice private")
    )
    await storage_backend.save_preset(make_preset(user_id=bob.id, name="bob private"))

    assert [preset.name for preset in await storage_backend.list_presets(None)] == [
        "builtin"
    ]
    assert {preset.name for preset in await storage_backend.list_presets(alice.id)} == {
        "builtin",
        "alice private",
    }
    assert {preset.name for preset in await storage_backend.list_presets(bob.id)} == {
        "builtin",
        "bob private",
    }
    assert (await storage_backend.get_preset(alice_private.id)).name == "alice private"

    updated = await storage_backend.save_preset(
        Preset(
            id=alice_private.id,
            user_id=alice.id,
            name="alice updated",
            description="updated",
            system_prompt="updated prompt",
            is_builtin=False,
            created_at=alice_private.created_at,
            updated_at=alice_private.updated_at,
        )
    )
    assert updated.name == "alice updated"

    assert await storage_backend.delete_preset(alice_private.id) is True
    assert await storage_backend.get_preset_by_id(alice_private.id) is None
    assert await storage_backend.delete_preset(alice_private.id) is False
    assert await storage_backend.get_preset_by_id(builtin.id) is not None


async def test_user_config_upsert_and_list(
    storage_backend: SQLiteBackend | FileBackend,
    make_user: Callable[..., User],
    make_user_config: Callable[..., UserConfig],
) -> None:
    alice = await storage_backend.save_user(make_user("alice"))
    saved = await storage_backend.save_user_config(
        make_user_config(alice.id, key="theme", value="dark")
    )
    overwritten = await storage_backend.save_user_config(
        make_user_config(alice.id, key="theme", value="light")
    )
    language = await storage_backend.save_user_config(
        make_user_config(alice.id, key="language", value="en")
    )

    assert overwritten.id == saved.id
    assert (await storage_backend.get_user_config(alice.id, "theme")).value == "light"
    assert [item.key for item in await storage_backend.list_user_configs(alice.id)] == [
        "language",
        "theme",
    ]
    assert language.id != saved.id


async def test_delete_session_cascades_messages(
    storage_backend: SQLiteBackend | FileBackend,
    make_user: Callable[..., User],
    make_session: Callable[..., Session],
    make_message: Callable[..., Message],
) -> None:
    alice = await storage_backend.save_user(make_user("alice"))
    session = await storage_backend.save_session(make_session(alice.id))
    await storage_backend.save_message(make_message(session.id, content="keep local"))

    assert await storage_backend.delete_session(session.id) is True
    assert await storage_backend.get_session(session.id) is None
    assert await storage_backend.list_messages(session.id) == []
    assert await storage_backend.delete_session(session.id) is False


async def test_delete_user_cascades_owned_data_and_preserves_other_users(
    storage_backend: SQLiteBackend | FileBackend,
    make_user: Callable[..., User],
    make_session: Callable[..., Session],
    make_message: Callable[..., Message],
    make_preset: Callable[..., Preset],
    make_user_config: Callable[..., UserConfig],
) -> None:
    alice = await storage_backend.save_user(make_user("alice"))
    bob = await storage_backend.save_user(make_user("bob"))
    alice_preset = await storage_backend.save_preset(
        make_preset(user_id=alice.id, name="alice preset")
    )
    bob_preset = await storage_backend.save_preset(
        make_preset(user_id=bob.id, name="bob preset")
    )
    alice_session = await storage_backend.save_session(
        make_session(alice.id, preset_id=alice_preset.id)
    )
    bob_session = await storage_backend.save_session(
        make_session(bob.id, title="bob session", preset_id=bob_preset.id)
    )
    await storage_backend.save_message(make_message(alice_session.id, content="alice"))
    await storage_backend.save_message(make_message(bob_session.id, content="bob"))
    await storage_backend.save_user_config(
        make_user_config(alice.id, key="theme", value="dark")
    )
    await storage_backend.save_user_config(
        make_user_config(bob.id, key="theme", value="light")
    )

    assert await storage_backend.delete_user(alice.id) is True
    assert await storage_backend.delete_user(alice.id) is False
    assert await storage_backend.get_user_by_id(alice.id) is None
    assert await storage_backend.get_session(alice_session.id) is None
    assert await storage_backend.list_messages(alice_session.id) == []
    assert await storage_backend.get_preset_by_id(alice_preset.id) is None
    assert await storage_backend.get_user_config(alice.id, "theme") is None

    assert await storage_backend.get_user_by_id(bob.id) is not None
    assert await storage_backend.get_session(bob_session.id) is not None
    assert len(await storage_backend.list_messages(bob_session.id)) == 1
    assert await storage_backend.get_preset_by_id(bob_preset.id) is not None
    assert (await storage_backend.get_user_config(bob.id, "theme")).value == "light"


async def test_file_backend_reloads_existing_data(
    file_backend: FileBackend,
    make_user: Callable[..., User],
) -> None:
    alice = await file_backend.save_user(make_user("alice"))
    base_path = file_backend.base_path
    await file_backend.close()

    restored = FileBackend(base_path)
    await restored.initialize()
    try:
        assert (await restored.get_user_by_username("alice")).id == alice.id
    finally:
        await restored.close()


async def test_file_backend_corrupt_json_is_not_silently_cleared(
    file_backend: FileBackend,
) -> None:
    users_path = file_backend.base_path / "users.json"
    users_path.write_text('[{"id": 1, "username": "alice"', encoding="utf-8")

    with pytest.raises(RuntimeError):
        await file_backend.list_users()

    assert users_path.read_text(encoding="utf-8").startswith('[{"id": 1')
    with pytest.raises(json.JSONDecodeError):
        json.loads(users_path.read_text(encoding="utf-8"))
