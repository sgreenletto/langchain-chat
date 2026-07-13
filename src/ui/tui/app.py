"""Rich-based TUI application."""

from rich.table import Table

from core.config_manager import AppConfig
from core.user_manager import UserManager
from interface.ui_protocol import AbstractUI
from models.schemas import User
from storage.base import StorageBackend
from ui.tui import menu_view
from ui.tui.chat_view import start_chat
from ui.tui.widgets import (
    console,
    read_choice,
    read_text,
    show_banner,
    show_error,
    show_info,
    show_menu,
    show_separator,
    show_success,
    show_warning,
)


class TUIApp(AbstractUI):
    """Terminal UI application."""

    def __init__(self, config: AppConfig, backend: StorageBackend) -> None:
        self.config = config
        self.backend = backend
        self.user_manager = UserManager(backend)
        self.current_user: User | None = None
        self.current_session = None
        self.menu_options = [
            "用户管理",
            "会话管理",
            "预设管理",
            "开始对话",
            "设置",
            "关于",
            "退出",
        ]
        self.user_menu_options = [
            "创建用户",
            "列出所有用户",
            "切换当前用户",
            "删除用户",
            "返回主菜单",
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
                self._show_current_user()
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
                await self._show_user_menu()
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

    def _show_current_user(self) -> None:
        if self.current_user is None:
            show_info("当前用户：未登录")
            return

        show_info(
            f"当前用户：{self.current_user.username}（id={self.current_user.id}）"
        )

    async def _show_user_menu(self) -> None:
        while True:
            show_separator()
            self._show_current_user()
            await self.display_menu("用户管理", self.user_menu_options)
            choice = await read_choice()

            match choice:
                case "1":
                    await self._create_user()
                case "2":
                    await self._list_users()
                case "3":
                    await self._switch_user()
                case "4":
                    await self._delete_user()
                case "5":
                    return
                case _:
                    await self.display_error("无效菜单编号，请输入 1-5。")

    async def _create_user(self) -> None:
        username = await self.get_user_input("请输入新用户名（直接回车取消）：")
        if not username:
            show_warning("已取消创建用户。")
            return

        try:
            user = await self.user_manager.create_user(
                username,
                default_model=self.config.llm.default_model,
            )
        except ValueError as exc:
            await self.display_error(str(exc))
            return

        show_success(f"用户创建成功：{user.username}（id={user.id}）")
        if self.current_user is None:
            self.current_user = user
            self.current_session = None
            show_info(f"已自动切换为当前用户：{user.username}")

    async def _list_users(self) -> None:
        users = await self.user_manager.list_users()
        if not users:
            show_info("当前没有任何用户。")
            return

        table = Table(title="用户列表", show_header=True, header_style="bold cyan")
        table.add_column("ID", justify="right")
        table.add_column("用户名")
        table.add_column("默认模型")
        table.add_column("创建时间")
        table.add_column("当前用户", justify="center")

        current_user_id = self.current_user.id if self.current_user else None
        for user in users:
            table.add_row(
                str(user.id),
                user.username,
                user.default_model or "未设置",
                user.created_at.astimezone().strftime("%Y-%m-%d %H:%M:%S"),
                "是" if user.id == current_user_id else "",
            )

        console.print(table)

    async def _switch_user(self) -> None:
        username = await self.get_user_input("请输入要切换到的用户名：")
        if not username:
            show_warning("已取消切换用户。")
            return

        user = await self.user_manager.get_user(username)
        if user is None:
            await self.display_error(f"用户 '{username.strip()}' 不存在。")
            return

        self.current_user = user
        self.current_session = None
        show_success(f"已切换到用户：{user.username}（id={user.id}）")

    async def _delete_user(self) -> None:
        username = await self.get_user_input("请输入要删除的用户名：")
        if not username:
            show_warning("已取消删除用户。")
            return

        user = await self.user_manager.get_user(username)
        if user is None:
            await self.display_error(f"用户 '{username.strip()}' 不存在。")
            return

        if self.current_user is not None and user.id == self.current_user.id:
            show_warning("不能删除当前登录用户，请先切换到其他用户。")
            return

        confirm = await self.get_user_input(
            f"确认删除用户 '{user.username}'？输入 yes 确认："
        )
        if confirm != "yes":
            show_info("已取消删除用户。")
            return

        try:
            deleted_user = await self.user_manager.delete_user(user.username)
        except ValueError as exc:
            await self.display_error(str(exc))
            return

        show_success(
            f"用户 '{deleted_user.username}' 已删除，关联数据已由数据库级联清理。"
        )
