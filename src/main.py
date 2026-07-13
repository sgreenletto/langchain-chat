"""Application entry point for langchain-chat Step 2."""

import asyncio
import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from core.config_manager import ConfigError, get_config
from ui.tui.app import TUIApp


async def async_main() -> None:
    """Load configuration and start the TUI."""
    try:
        config = get_config()
    except ConfigError as exc:
        print(f"配置错误：{exc}")
        raise SystemExit(1) from exc

    app = TUIApp(config)
    await app.run()


if __name__ == "__main__":
    asyncio.run(async_main())
