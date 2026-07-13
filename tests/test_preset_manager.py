"""Unit tests for PresetManager business behavior."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from src.models.schemas import User

pytestmark = pytest.mark.asyncio


def import_preset_manager():
    src_dir = Path(__file__).resolve().parents[1] / "src"
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    from core.preset_manager import PresetManager

    return PresetManager


def write_builtin_presets(path: Path) -> None:
    path.write_text(
        """
presets:
  - name: builtin
    description: system preset
    system_prompt: You are the built-in assistant.
""",
        encoding="utf-8",
    )


async def test_load_builtin_presets_is_idempotent(storage_backend, tmp_path) -> None:
    presets_path = tmp_path / "presets.yaml"
    write_builtin_presets(presets_path)
    manager = import_preset_manager()(storage_backend, presets_path)

    assert await manager.load_builtin_presets() == 1
    assert await manager.load_builtin_presets() == 0

    presets = await manager.list_presets(user_id=1)
    assert len(presets) == 1
    assert presets[0].name == "builtin"
    assert presets[0].is_builtin is True


async def test_custom_preset_crud_and_user_isolation(storage_backend) -> None:
    manager = import_preset_manager()(storage_backend)
    alice = await storage_backend.save_user(User(id=0, username="alice"))
    bob = await storage_backend.save_user(User(id=0, username="bob"))

    preset = await manager.create_preset(
        alice.id,
        name="custom",
        description="desc",
        system_prompt="prompt",
    )
    assert preset.user_id == alice.id
    assert preset.is_builtin is False
    assert {item.name for item in await manager.list_presets(alice.id)} == {"custom"}
    assert await manager.list_presets(bob.id) == []

    updated = await manager.update_preset(
        preset.id,
        alice.id,
        name="custom updated",
        description="new",
        system_prompt="new prompt",
    )
    assert updated.name == "custom updated"
    assert updated.description == "new"

    with pytest.raises(ValueError):
        await manager.update_preset(preset.id, bob.id, "bad", "", "bad")
    deleted = await manager.delete_preset(preset.id, alice.id)
    assert deleted.id == preset.id
    assert await manager.get_preset(preset.id) is None


async def test_rejects_invalid_custom_preset_input(storage_backend) -> None:
    manager = import_preset_manager()(storage_backend)
    user = await storage_backend.save_user(User(id=0, username="alice"))

    with pytest.raises(ValueError):
        await manager.create_preset(user.id, "", "", "prompt")
    with pytest.raises(ValueError):
        await manager.create_preset(user.id, "name", "", "")
    with pytest.raises(ValueError):
        await manager.create_preset(9999, "name", "", "prompt")
