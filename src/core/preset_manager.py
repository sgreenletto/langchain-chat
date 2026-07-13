"""Preset management business layer."""

import logging
from pathlib import Path

import yaml

from models.schemas import Preset, utc_now
from storage.base import StorageBackend

logger = logging.getLogger(__name__)


class PresetManager:
    """Manage built-in and user-defined presets."""

    def __init__(self, backend: StorageBackend, presets_path: str | Path | None = None):
        self.backend = backend
        self.presets_path = Path(presets_path) if presets_path else self._default_path()

    async def load_builtin_presets(self) -> int:
        """Load built-in presets from config/presets.yaml idempotently."""
        data = self._load_presets_yaml()
        preset_items = data.get("presets")
        if preset_items is None:
            raise ValueError("内置预设配置缺少 presets 字段。")
        if not isinstance(preset_items, list):
            raise ValueError("内置预设配置 presets 字段必须是列表。")

        existing_builtin_names = {
            preset.name
            for preset in await self.backend.list_presets(user_id=None)
            if preset.is_builtin
        }

        imported_count = 0
        for item in preset_items:
            if not isinstance(item, dict):
                continue

            name = str(item.get("name", "")).strip()
            system_prompt = str(item.get("system_prompt", "")).strip()
            if not name or not system_prompt:
                continue
            if name in existing_builtin_names:
                continue

            description = str(item.get("description", "")).strip()
            await self.backend.save_preset(
                Preset(
                    id=0,
                    user_id=None,
                    name=name,
                    description=description,
                    system_prompt=system_prompt,
                    is_builtin=True,
                )
            )
            existing_builtin_names.add(name)
            imported_count += 1

        if imported_count:
            logger.info(
                "Built-in presets loaded",
                extra={"operation": "load_builtin_presets", "status": "ok"},
            )
        return imported_count

    async def list_presets(self, user_id: int) -> list[Preset]:
        """List built-in presets and the current user's custom presets."""
        return await self.backend.list_presets(user_id=user_id)

    async def get_preset(self, preset_id: int) -> Preset | None:
        """Return a preset by id."""
        return await self.backend.get_preset_by_id(preset_id)

    async def create_preset(
        self,
        user_id: int,
        name: str,
        description: str,
        system_prompt: str,
    ) -> Preset:
        """Create a user-defined preset."""
        await self._require_user(user_id)
        normalized_name = self._require_text(name, "预设名称不能为空。")
        normalized_prompt = self._require_text(system_prompt, "系统提示词不能为空。")
        await self._ensure_no_builtin_name_conflict(normalized_name)

        saved = await self.backend.save_preset(
            Preset(
                id=0,
                user_id=user_id,
                name=normalized_name,
                description=description.strip(),
                system_prompt=normalized_prompt,
                is_builtin=False,
            )
        )
        logger.info(
            "Custom preset created",
            extra={
                "user_id": user_id,
                "operation": "create_preset",
                "status": "ok",
            },
        )
        return saved

    async def update_preset(
        self,
        preset_id: int,
        user_id: int,
        name: str,
        description: str,
        system_prompt: str,
    ) -> Preset:
        """Update a user-defined preset."""
        preset = await self._require_owned_custom_preset(preset_id, user_id)
        normalized_name = self._require_text(name, "预设名称不能为空。")
        normalized_prompt = self._require_text(system_prompt, "系统提示词不能为空。")
        await self._ensure_no_builtin_name_conflict(normalized_name)

        updated_preset = Preset(
            id=preset.id,
            user_id=preset.user_id,
            name=normalized_name,
            description=description.strip(),
            system_prompt=normalized_prompt,
            is_builtin=False,
            created_at=preset.created_at,
            updated_at=utc_now(),
        )
        saved = await self.backend.save_preset(updated_preset)
        logger.info(
            "Custom preset updated",
            extra={
                "user_id": user_id,
                "operation": "update_preset",
                "status": "ok",
            },
        )
        return saved

    async def delete_preset(self, preset_id: int, user_id: int) -> Preset:
        """Delete a user-defined preset."""
        preset = await self._require_owned_custom_preset(preset_id, user_id)
        deleted = await self.backend.delete_preset(preset.id)
        if not deleted:
            logger.error(
                "Custom preset delete failed",
                extra={
                    "user_id": user_id,
                    "operation": "delete_preset",
                    "status": "failed",
                },
            )
            raise ValueError(f"删除预设失败：id={preset.id}")
        logger.info(
            "Custom preset deleted",
            extra={
                "user_id": user_id,
                "operation": "delete_preset",
                "status": "ok",
            },
        )
        return preset

    def _load_presets_yaml(self) -> dict:
        if not self.presets_path.exists():
            raise FileNotFoundError(f"内置预设文件不存在：{self.presets_path}")

        try:
            with self.presets_path.open("r", encoding="utf-8") as file:
                data = yaml.safe_load(file) or {}
        except yaml.YAMLError as exc:
            logger.exception(
                "Built-in preset YAML parse failed",
                extra={
                    "operation": "load_builtin_presets",
                    "status": "failed",
                    "error_type": type(exc).__name__,
                    "path": str(self.presets_path),
                },
            )
            raise ValueError("内置预设 YAML 格式错误。") from exc

        if not isinstance(data, dict):
            raise ValueError("内置预设配置顶层必须是映射结构。")
        return data

    async def _require_user(self, user_id: int) -> None:
        if await self.backend.get_user_by_id(user_id) is None:
            raise ValueError(f"用户不存在：id={user_id}")

    async def _ensure_no_builtin_name_conflict(self, name: str) -> None:
        presets = await self.backend.list_presets(user_id=None)
        for preset in presets:
            if preset.is_builtin and preset.name == name:
                raise ValueError(f"预设名称 '{name}' 与系统内置预设冲突。")

    async def _require_owned_custom_preset(
        self,
        preset_id: int,
        user_id: int,
    ) -> Preset:
        preset = await self.backend.get_preset_by_id(preset_id)
        if preset is None:
            raise ValueError(f"预设不存在：id={preset_id}")
        if preset.is_builtin:
            raise ValueError("系统内置预设不允许修改或删除。")
        if preset.user_id != user_id:
            raise ValueError("不能修改或删除其他用户的自定义预设。")
        return preset

    @staticmethod
    def _require_text(value: str, message: str) -> str:
        normalized_value = value.strip()
        if not normalized_value:
            raise ValueError(message)
        return normalized_value

    @staticmethod
    def _default_path() -> Path:
        return Path(__file__).resolve().parents[2] / "config" / "presets.yaml"
