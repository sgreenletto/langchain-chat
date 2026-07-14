"""Application entry point for langchain-chat Step 7."""

import asyncio
import logging
import logging.config
import sys
from pathlib import Path

import yaml

SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from core.chat_engine import ChatEngine  # noqa: E402
from core.config_manager import ConfigError, get_config  # noqa: E402
from core.preset_manager import PresetManager  # noqa: E402
from core.session_manager import SessionManager  # noqa: E402
from core.user_manager import UserManager  # noqa: E402
from storage.factory import StorageFactory  # noqa: E402
from ui.tui.app import TUIApp  # noqa: E402

logger = logging.getLogger(__name__)


def setup_logging() -> None:
    """Configure logging before business components are initialized."""
    logs_dir = SRC_DIR.parent / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    config_path = SRC_DIR.parent / "config" / "logging.yaml"
    try:
        with config_path.open("r", encoding="utf-8") as file:
            logging.config.dictConfig(yaml.safe_load(file))
    except Exception as exc:
        print(f"日志初始化失败：{exc}", file=sys.stderr)
        raise SystemExit(1) from exc


async def async_main() -> None:
    """Load configuration, initialize storage, load presets, and start the TUI."""
    setup_logging()
    logger.info("Application starting", extra={"status": "starting"})
    backend = None
    chat_engine = None
    try:
        config = get_config()
        logger.info(
            "Configuration loaded",
            extra={
                "app_env": config.app_env,
                "config_files": [path.name for path in config.config_files],
                "storage_type": config.storage.type,
                "status": "ok",
            },
        )
    except ConfigError as exc:
        logger.error(
            "Configuration load failed",
            extra={"status": "failed", "error_type": type(exc).__name__},
        )
        print(f"配置错误：{exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    try:
        backend = StorageFactory.create(config.storage.type)
        await backend.initialize()
        logger.info(
            "Storage backend initialized",
            extra={"storage_type": config.storage.type, "status": "ok"},
        )
        user_manager = UserManager(backend, config)
        preset_manager = PresetManager(backend)
        session_manager = SessionManager(backend, config=config)
        chat_engine = ChatEngine(config)
        logger.info(
            "Chat engine initialized",
            extra={"model": config.default_model_alias, "status": "ok"},
        )
        imported_count = await preset_manager.load_builtin_presets()
        if imported_count > 0:
            print(f"已导入 {imported_count} 个系统内置预设。")
            logger.info(
                "Built-in presets imported",
                extra={"operation": "load_builtin_presets", "status": "ok"},
            )
        app = TUIApp(
            config=config,
            backend=backend,
            user_manager=user_manager,
            preset_manager=preset_manager,
            session_manager=session_manager,
            chat_engine=chat_engine,
        )
        logger.info("TUI starting", extra={"status": "starting"})
        await app.run()
    except KeyboardInterrupt:
        print("已收到 Ctrl+C，正在退出。")
        logger.info("Application interrupted", extra={"status": "interrupted"})
    except Exception as exc:
        logger.exception(
            "Application failed",
            extra={"status": "failed", "error_type": type(exc).__name__},
        )
        print(f"启动或运行失败：{exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    finally:
        if chat_engine is not None:
            await chat_engine.close()
        if backend is not None:
            await backend.close()
        logger.info("Application shutdown complete", extra={"status": "stopped"})


if __name__ == "__main__":
    asyncio.run(async_main())
