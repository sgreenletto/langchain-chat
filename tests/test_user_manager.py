"""Unit tests for UserManager business behavior."""

from __future__ import annotations

import pytest
from src.core.user_manager import UserManager
from src.models.schemas import Preset, Session, User
from src.storage.file_backend import FileBackend
from src.storage.sqlite_backend import SQLiteBackend

pytestmark = pytest.mark.asyncio


async def test_create_list_and_get_user(user_manager: UserManager) -> None:
    alice = await user_manager.create_user("  alice  ")
    bob = await user_manager.create_user("bob", default_model="backup")

    assert alice.username == "alice"
    assert bob.default_model == "backup"
    assert await user_manager.get_user(" alice ") == alice
    assert await user_manager.get_user_by_id(bob.id) == bob
    assert [user.username for user in await user_manager.list_users()] == [
        "alice",
        "bob",
    ]


async def test_rejects_empty_and_duplicate_usernames(
    user_manager: UserManager,
) -> None:
    with pytest.raises(ValueError):
        await user_manager.create_user("   ")

    await user_manager.create_user("alice")
    with pytest.raises(ValueError):
        await user_manager.create_user(" alice ")

    assert await user_manager.get_user("   ") is None


async def test_delete_user_and_missing_user_errors(user_manager: UserManager) -> None:
    alice = await user_manager.create_user("alice")

    deleted = await user_manager.delete_user("alice")
    assert deleted.id == alice.id
    assert await user_manager.get_user("alice") is None

    with pytest.raises(ValueError):
        await user_manager.delete_user("alice")
    with pytest.raises(ValueError):
        await user_manager.delete_user("   ")


async def test_delete_current_state_is_not_owned_by_user_manager(
    user_manager: UserManager,
) -> None:
    alice = await user_manager.create_user("alice")
    bob = await user_manager.create_user("bob")

    deleted = await user_manager.delete_user("bob")

    assert deleted.id == bob.id
    assert await user_manager.get_user_by_id(alice.id) is not None
    assert await user_manager.get_user_by_id(bob.id) is None


async def test_update_default_model_and_preserve_default_preset(
    user_manager: UserManager,
    storage_backend: SQLiteBackend | FileBackend,
) -> None:
    alice = await user_manager.create_user("alice")
    preset = await storage_backend.save_preset(
        Preset(id=0, user_id=alice.id, name="default", system_prompt="prompt")
    )
    updated_with_preset = User(
        id=alice.id,
        username=alice.username,
        default_model=alice.default_model,
        default_preset_id=preset.id,
        created_at=alice.created_at,
        updated_at=alice.updated_at,
    )
    await storage_backend.save_user(updated_with_preset)

    updated = await user_manager.update_default_model(alice.id, "backup")

    assert updated.default_model == "backup"
    assert updated.default_preset_id == preset.id
    assert user_manager.get_effective_default_model(updated) == "backup"


async def test_update_default_model_rejects_missing_model_and_user(
    user_manager: UserManager,
) -> None:
    alice = await user_manager.create_user("alice")

    with pytest.raises(ValueError):
        await user_manager.update_default_model(alice.id, "missing")
    with pytest.raises(ValueError):
        await user_manager.update_default_model(9999, "backup")

    invalid = User(id=alice.id, username="alice", default_model="does-not-exist")
    assert user_manager.get_effective_default_model(invalid) == "default"


async def test_user_manager_does_not_bypass_storage_user_isolation(
    user_manager: UserManager,
    storage_backend: SQLiteBackend | FileBackend,
) -> None:
    alice = await user_manager.create_user("alice")
    bob = await user_manager.create_user("bob")
    alice_session = await storage_backend.save_session(
        Session(id=0, user_id=alice.id, title="alice session", model_name="default")
    )
    bob_session = await storage_backend.save_session(
        Session(id=0, user_id=bob.id, title="bob session", model_name="default")
    )

    await user_manager.delete_user("alice")

    assert await storage_backend.get_session(alice_session.id) is None
    assert await storage_backend.get_session(bob_session.id) is not None
