"""Rich-based TUI application skeleton."""

from core.config_manager import AppConfig
from interface.ui_protocol import AbstractUI
from ui.tui import menu_view
from ui.tui.chat_view import start_chat
from ui.tui.widgets import (
    read_choice,
    read_text,
    show_banner,
    show_error,
    show_info,
    show_menu,
    show_success,
)


class TUIApp(AbstractUI):
    """Terminal UI skeleton for Step 2."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.menu_options = [
            "用户管理",
            "会话管理",
            "预设管理",
            "开始对话",
            "设置",
            "关于",
            "退出",
        ]

    async def display_message(self, message: str) -> None:
        show_info(message)

    async def get_user_input(self, prompt: str) -> str:
        return await read_text(prompt)

    async def display_menu(self, title: str, options: list[str]) -> None:
        show_menu(title, options)

    async def display_error(self, message: str) -> None:
        show_error(message)

    async def display_info(self, message: str) -> None:
        show_info(message)

    async def run(self) -> None:
        """Run the async TUI main loop."""
        show_banner()
        show_success(f"已加载配置：{self.config.app.name} v{self.config.app.version}")

        while True:
            try:
                await self.display_menu("主菜单", self.menu_options)
                choice = await read_choice()
                should_exit = await self._handle_choice(choice)
                if should_exit:
                    show_success("已退出 langchain-chat。")
                    return
            except KeyboardInterrupt:
                show_info("已收到 Ctrl+C，正在退出。")
                return

    async def _handle_choice(self, choice: str) -> bool:
        match choice:
            case "1":
                await menu_view.show_user_management()
            case "2":
                await menu_view.show_session_management()
            case "3":
                await menu_view.show_preset_management()
            case "4":
                await start_chat()
            case "5":
                await menu_view.show_settings()
            case "6":
                await menu_view.show_about()
            case "7":
                return True
            case _:
                await self.display_error("无效菜单编号，请输入 1-7。")
        return False
