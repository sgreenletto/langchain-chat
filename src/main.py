"""Step 1 startup entry for langchain-chat."""

import platform
import sys
from datetime import datetime

APP_NAME = "langchain-chat"
APP_VERSION = "0.1.0"
CURRENT_STEP = "Step 1：项目初始化与工程化配置"


def print_banner() -> None:
    """Print the Step 1 startup banner."""
    python_version = platform.python_version()
    runtime_platform = platform.platform()
    started_at = datetime.now().astimezone().isoformat(timespec="seconds")

    banner_lines = [
        "=" * 60,
        f"应用名称: {APP_NAME}",
        f"应用版本: {APP_VERSION}",
        f"Python 版本: {python_version}",
        f"运行平台: {runtime_platform}",
        f"启动时间: {started_at}",
        f"当前 Step: {CURRENT_STEP}",
        "=" * 60,
    ]
    print("\n".join(banner_lines))


def main() -> None:
    """Run the application entry point for Step 1."""
    print_banner()


if __name__ == "__main__":
    main()
