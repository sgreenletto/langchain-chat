"""Rich-based TUI application."""

from rich.markup import escape
from rich.table import Table

from core.chat_engine import ChatEngine
from core.config_manager import AppConfig
from core.preset_manager import PresetManager
from core.session_manager import SessionManager
from core.user_manager import UserManager
from interface.ui_protocol import AbstractUI
from models.schemas import Preset, Session, User
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

    def __init__(
        self,
        config: AppConfig,
        backend: StorageBackend,
        user_manager: UserManager | None = None,
        preset_manager: PresetManager | None = None,
        session_manager: SessionManager | None = None,
        chat_engine: ChatEngine | None = None,
    ) -> None:
        self.config = config
        self.user_manager = user_manager or UserManager(backend)
        self.preset_manager = preset_manager or PresetManager(backend)
        self.session_manager = session_manager or SessionManager(backend)
        self.chat_engine = chat_engine or ChatEngine(config)
        self.current_user: User | None = None
        self.current_session = None
        self.menu_options = [
            "用户管理",
            "会话管理",
            "预设管理",
            "开始对话",
            "搜索历史消息",
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
        self.preset_menu_options = [
            "列出所有预设",
            "新增自定义预设",
            "编辑自定义预设",
            "删除自定义预设",
            "返回主菜单",
        ]
        self.session_menu_options = [
            "查看会话列表",
            "查看会话记录",
            "加载会话",
            "重命名会话",
            "删除会话",
            "返回主菜单",
        ]

    async def display_message(self, message: str) -> None:
        show_info(message)

    async def get_user_input(self, prompt: str, default: str = "") -> str:
        return await read_text(prompt, default=default)

    async def display_menu(self, title: str, options: list[str]) -> None:
        show_menu(title, options)

    async def display_error(self, message: str) -> None:
        show_error(message)

    async def display_info(self, message: str) -> None:
        show_info(message)

    async def run(self) -> None:
        """Run the async TUI main loop."""
        show_banner(self.config.current_step)
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
                await self._show_session_menu()
            case "3":
                await self._show_preset_menu()
            case "4":
                await start_chat(self)
            case "5":
                await self._search_messages()
            case "6":
                await menu_view.show_settings()
            case "7":
                await menu_view.show_about()
            case "8":
                return True
            case _:
                await self.display_error("无效菜单编号，请输入 1-8。")
        return False

    def _show_current_user(self) -> None:
        if self.current_user is None:
            show_info("当前用户：未登录")
            return

        show_info(
            f"当前用户：{self.current_user.username}"
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
                default_model=self.config.model_name,
            )
        except ValueError as exc:
            await self.display_error(str(exc))
            return

        show_success(f"用户创建成功：{user.username}")
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
        table.add_column("序号", justify="right")
        table.add_column("用户名")
        table.add_column("默认模型")
        table.add_column("创建时间")
        table.add_column("当前用户", justify="center")

        current_user_id = self.current_user.id if self.current_user else None
        for display_index, user in enumerate(users, start=1):
            table.add_row(
                str(display_index),
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
        show_success(f"已切换到用户：{user.username}")

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

    async def _show_preset_menu(self) -> None:
        if not self._require_login():
            return

        while True:
            show_separator()
            self._show_current_user()
            await self.display_menu("预设管理", self.preset_menu_options)
            choice = await read_choice()

            match choice:
                case "1":
                    await self._list_presets()
                case "2":
                    await self._create_preset()
                case "3":
                    await self._edit_preset()
                case "4":
                    await self._delete_preset()
                case "5":
                    return
                case _:
                    await self.display_error("无效菜单编号，请输入 1-5。")

    def _require_login(self) -> bool:
        if self.current_user is None:
            show_warning("请先创建或切换用户。")
            return False
        return True

    async def _list_presets(self) -> None:
        if self.current_user is None:
            show_warning("请先创建或切换用户。")
            return

        presets = await self.preset_manager.list_presets(self.current_user.id)
        if not presets:
            show_info("当前没有任何预设。")
            return

        table = Table(title="预设列表", show_header=True, header_style="bold cyan")
        table.add_column("序号", justify="right")
        table.add_column("名称")
        table.add_column("描述")
        table.add_column("类型", justify="center")
        table.add_column("系统提示词预览")

        for display_index, preset in enumerate(presets, start=1):
            table.add_row(
                str(display_index),
                preset.name,
                preset.description or "",
                "内置" if preset.is_builtin else "自定义",
                self._preview_prompt(preset.system_prompt),
            )

        console.print(table)

    async def _create_preset(self) -> None:
        if self.current_user is None:
            show_warning("请先创建或切换用户。")
            return

        name = await self.get_user_input("请输入预设名称：")
        description = await self.get_user_input("请输入预设描述（可留空）：")
        system_prompt = await self.get_user_input("请输入系统提示词：")

        try:
            preset = await self.preset_manager.create_preset(
                user_id=self.current_user.id,
                name=name,
                description=description,
                system_prompt=system_prompt,
            )
        except ValueError as exc:
            await self.display_error(str(exc))
            return

        show_success(f"预设创建成功：{preset.name}")

    async def _edit_preset(self) -> None:
        if self.current_user is None:
            show_warning("请先创建或切换用户。")
            return

        custom_presets = await self._list_current_user_custom_presets(
            "可编辑的自定义预设"
        )
        if not custom_presets:
            show_info("当前用户没有可编辑的自定义预设。")
            return

        preset = await self._read_preset_selection(
            "请输入要编辑的预设序号：",
            custom_presets,
        )
        if preset is None:
            return

        preset = await self._get_editable_custom_preset(preset.id)
        if preset is None:
            return

        name = await self.get_user_input("预设名称", default=preset.name)
        description = await self.get_user_input("预设描述", default=preset.description)
        system_prompt = await self.get_user_input(
            "系统提示词",
            default=preset.system_prompt,
        )

        try:
            updated = await self.preset_manager.update_preset(
                preset_id=preset.id,
                user_id=self.current_user.id,
                name=name,
                description=description,
                system_prompt=system_prompt,
            )
        except ValueError as exc:
            await self.display_error(str(exc))
            return

        show_success(f"预设已更新：{updated.name}")

    async def _delete_preset(self) -> None:
        if self.current_user is None:
            show_warning("请先创建或切换用户。")
            return

        custom_presets = await self._list_current_user_custom_presets(
            "可删除的自定义预设"
        )
        if not custom_presets:
            show_info("当前用户没有可删除的自定义预设。")
            return

        preset = await self._read_preset_selection(
            "请输入要删除的预设序号：",
            custom_presets,
        )
        if preset is None:
            return

        preset = await self._get_editable_custom_preset(preset.id)
        if preset is None:
            return

        confirm = await self.get_user_input(
            f"确认删除预设 '{preset.name}'？输入 yes 确认："
        )
        if confirm != "yes":
            show_info("已取消删除预设。")
            return

        try:
            deleted = await self.preset_manager.delete_preset(
                preset_id=preset.id,
                user_id=self.current_user.id,
            )
        except ValueError as exc:
            await self.display_error(str(exc))
            return

        show_success(f"预设“{deleted.name}”已删除")

    async def _list_current_user_custom_presets(self, title: str) -> list[Preset]:
        if self.current_user is None:
            return []

        presets = await self.preset_manager.list_presets(self.current_user.id)
        custom_presets = [preset for preset in presets if not preset.is_builtin]

        if custom_presets:
            table = Table(title=title, show_header=True, header_style="bold cyan")
            table.add_column("序号", justify="right")
            table.add_column("名称")
            table.add_column("描述")
            for display_index, preset in enumerate(custom_presets, start=1):
                table.add_row(
                    str(display_index),
                    preset.name,
                    preset.description or "",
                )
            console.print(table)

        return custom_presets

    async def _read_preset_selection(
        self,
        prompt: str,
        presets: list[Preset],
    ) -> Preset | None:
        raw_value = await self.get_user_input(prompt)
        try:
            display_index = int(raw_value)
        except ValueError:
            await self.display_error("请输入有效的列表序号。")
            return None
        selection_map = self._build_selection_map(presets)
        preset = selection_map.get(display_index)
        if preset is None:
            await self.display_error(f"列表序号无效，请输入 1-{len(presets)}。")
            return None
        return preset

    async def _get_editable_custom_preset(self, preset_id: int) -> Preset | None:
        if self.current_user is None:
            show_warning("请先创建或切换用户。")
            return None

        preset = await self.preset_manager.get_preset(preset_id)
        if preset is None:
            await self.display_error("所选预设不存在或已被删除。")
            return None
        if preset.is_builtin:
            await self.display_error("系统内置预设不允许编辑或删除。")
            return None
        if preset.user_id != self.current_user.id:
            await self.display_error("不能编辑或删除其他用户的自定义预设。")
            return None
        return preset

    @staticmethod
    def _preview_prompt(prompt: str, max_length: int = 40) -> str:
        normalized_prompt = " ".join(prompt.split())
        if len(normalized_prompt) <= max_length:
            return normalized_prompt
        return f"{normalized_prompt[:max_length]}..."

    @staticmethod
    def _build_selection_map(presets: list[Preset]) -> dict[int, Preset]:
        return {
            display_index: preset
            for display_index, preset in enumerate(presets, start=1)
        }

    async def _show_session_menu(self) -> None:
        if not self._require_login():
            return

        while True:
            show_separator()
            self._show_current_user()
            await self.display_menu("会话管理", self.session_menu_options)
            choice = await read_choice()

            match choice:
                case "1":
                    await self._list_sessions()
                case "2":
                    await self._show_session_messages()
                case "3":
                    await self._load_session()
                case "4":
                    await self._rename_session()
                case "5":
                    await self._delete_session()
                case "6":
                    return
                case _:
                    await self.display_error("无效菜单编号，请输入 1-6。")

    async def _list_sessions(self) -> list[Session]:
        if self.current_user is None:
            show_warning("请先创建或切换用户。")
            return []

        sessions = await self.session_manager.list_sessions(self.current_user.id)
        if not sessions:
            show_info("当前用户还没有任何会话。")
            return []

        table = Table(title="会话列表", show_header=True, header_style="bold cyan")
        table.add_column("序号", justify="right")
        table.add_column("标题")
        table.add_column("模型")
        table.add_column("预设")
        table.add_column("创建时间")
        table.add_column("最后更新")
        table.add_column("累计 Token", justify="right")
        current_session_id = self.current_session.id if self.current_session else None

        for display_index, session in enumerate(sessions, start=1):
            preset = await self.session_manager.get_session_preset(session)
            title = session.title
            if session.id == current_session_id:
                title = f"{title}（当前）"
            table.add_row(
                str(display_index),
                title,
                session.model_name or "-",
                preset.name if preset else "无预设",
                session.created_at.astimezone().strftime("%Y-%m-%d %H:%M"),
                session.updated_at.astimezone().strftime("%Y-%m-%d %H:%M"),
                str(session.total_prompt_tokens + session.total_completion_tokens),
            )

        console.print(table)
        return sessions

    async def _load_session(self) -> None:
        session = await self._read_session_selection("请输入要加载的会话序号：")
        if session is None:
            return
        self.current_session = session
        show_success(f"已加载会话：{session.title}")

    async def _show_session_messages(self) -> None:
        if self.current_user is None:
            show_warning("请先创建或切换用户。")
            return

        session = await self._read_session_selection("请输入要查看记录的会话序号：")
        if session is None:
            return

        messages = await self.session_manager.get_session_messages(
            self.current_user.id,
            session.id,
        )
        if not messages:
            show_info("该会话还没有任何消息。")
            return

        show_separator()
        show_info(f"会话记录：{session.title}")
        for message in messages:
            role_name = self._display_message_role(message.role)
            console.print(
                f"[bold]{role_name}[/bold]：{escape(message.content)}"
            )
        show_separator()

    async def _rename_session(self) -> None:
        if self.current_user is None:
            show_warning("请先创建或切换用户。")
            return

        session = await self._read_session_selection("请输入要重命名的会话序号：")
        if session is None:
            return

        new_title = await self.get_user_input("请输入新标题：")
        try:
            renamed = await self.session_manager.rename_session(
                self.current_user.id,
                session.id,
                new_title,
            )
        except ValueError as exc:
            await self.display_error(str(exc))
            return

        if self.current_session is not None and self.current_session.id == renamed.id:
            self.current_session = renamed
        show_success(f"会话已重命名：{renamed.title}")
        await self._list_sessions()

    async def _delete_session(self) -> None:
        if self.current_user is None:
            show_warning("请先创建或切换用户。")
            return

        session = await self._read_session_selection("请输入要删除的会话序号：")
        if session is None:
            return

        confirm = await self.get_user_input(
            f"确认删除会话 '{session.title}'？输入 yes 确认："
        )
        if confirm != "yes":
            show_info("已取消删除会话。")
            return

        try:
            deleted = await self.session_manager.delete_session(
                self.current_user.id,
                session.id,
            )
        except ValueError as exc:
            await self.display_error(str(exc))
            return

        if self.current_session is not None and self.current_session.id == deleted.id:
            self.current_session = None
            show_info("已清空当前会话状态。")
        show_success(f"会话“{deleted.title}”已删除。")

    async def _read_session_selection(self, prompt: str) -> Session | None:
        if self.current_user is None:
            show_warning("请先创建或切换用户。")
            return None

        sessions = await self._list_sessions()
        if not sessions:
            return None

        raw_value = await self.get_user_input(prompt)
        try:
            display_index = int(raw_value)
        except ValueError:
            await self.display_error("请输入有效的会话序号。")
            return None

        selection_map = self._build_session_selection_map(sessions)
        session = selection_map.get(display_index)
        if session is None:
            await self.display_error(f"会话序号无效，请输入 1-{len(sessions)}。")
            return None
        try:
            return await self.session_manager.get_session(
                self.current_user.id,
                session.id,
            )
        except ValueError as exc:
            await self.display_error(str(exc))
            return None

    @staticmethod
    def _build_session_selection_map(sessions: list[Session]) -> dict[int, Session]:
        return {
            display_index: session
            for display_index, session in enumerate(sessions, start=1)
        }

    async def _search_messages(self) -> None:
        if self.current_user is None:
            show_warning("请先创建或切换用户。")
            return

        keyword = await self.get_user_input("请输入搜索关键词：")
        if not keyword.strip():
            show_warning("搜索关键词不能为空。")
            return

        messages = await self.session_manager.search_messages(
            self.current_user.id,
            keyword,
        )
        if not messages:
            show_info("没有找到匹配的历史消息。")
            return

        sessions = await self.session_manager.list_sessions(self.current_user.id)
        session_map = {session.id: session for session in sessions}
        grouped_messages: dict[int, list] = {}
        for message in messages:
            if message.session_id in session_map:
                grouped_messages.setdefault(message.session_id, []).append(message)

        show_separator()
        show_info(
            f"搜索结果：共 {len(messages)} 条，涉及 {len(grouped_messages)} 个会话。"
        )
        for display_index, (session_id, session_messages) in enumerate(
            grouped_messages.items(),
            start=1,
        ):
            session = session_map[session_id]
            console.print(
                f"[bold cyan]{display_index}. {escape(session.title)}[/bold cyan]"
            )
            for message in session_messages:
                role_name = self._display_message_role(message.role)
                console.print(
                    f"  [bold]{role_name}[/bold]：{escape(message.content)}"
                )
        show_separator()

    @staticmethod
    def _display_message_role(role: str) -> str:
        role_names = {
            "human": "用户",
            "ai": "AI",
            "system": "系统",
        }
        return role_names.get(role, role)
