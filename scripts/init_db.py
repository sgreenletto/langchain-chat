"""Initialize the configured storage backend."""

import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from core.config_manager import ConfigError, get_config  # noqa: E402
from storage.factory import StorageFactory  # noqa: E402

EXPECTED_TABLES = {"users", "sessions", "messages", "presets", "user_configs"}


async def initialize_storage() -> None:
    """Initialize tables for the configured storage backend."""
    config = get_config()
    backend = StorageFactory.create(config.storage.type)
    try:
        await backend.initialize()
        table_names_method = getattr(backend, "list_table_names", None)
        tables = set(await table_names_method()) if table_names_method else set()
        missing_tables = EXPECTED_TABLES - tables
        if missing_tables:
            raise RuntimeError(f"数据库缺少表：{sorted(missing_tables)}")

        print(f"存储后端已初始化：{backend.__class__.__name__}")
        print(f"存储类型：{config.storage.type}")
        print(f"五张表：{', '.join(sorted(tables))}")
    finally:
        await backend.close()


def main() -> None:
    """Run script with a non-zero exit code on failure."""
    try:
        asyncio.run(initialize_storage())
    except ConfigError as exc:
        print(f"配置错误：{exc}")
        raise SystemExit(1) from exc
    except Exception as exc:
        print(f"初始化失败：{type(exc).__name__}: {exc}")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
