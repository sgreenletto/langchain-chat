"""Application entry point for langchain-chat Step 5."""

import asyncio
import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from core.config_manager import ConfigError, get_config  # noqa: E402
from core.preset_manager import PresetManager  # noqa: E402
from storage.factory import StorageFactory  # noqa: E402
from ui.tui.app import TUIApp  # noqa: E402


async def async_main() -> None:
    """Load configuration, initialize storage, load presets, and start the TUI."""
    backend = None
    try:
        config = get_config()
    except ConfigError as exc:
        print(f"配置错误：{exc}")
        raise SystemExit(1) from exc

    try:
        backend = StorageFactory.create(config.storage.type)
        await backend.initialize()
        preset_manager = PresetManager(backend)
        imported_count = await preset_manager.load_builtin_presets()
        if imported_count > 0:
            print(f"已导入 {imported_count} 个系统内置预设。")
        app = TUIApp(config=config, backend=backend)
        await app.run()
    except KeyboardInterrupt:
        print("已收到 Ctrl+C，正在退出。")
    except Exception as exc:
        print(f"启动或运行失败：{exc}")
        raise SystemExit(1) from exc
    finally:
        if backend is not None:
            await backend.close()


if __name__ == "__main__":
    asyncio.run(async_main())
