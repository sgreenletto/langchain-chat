"""Menu placeholder views for features implemented in later steps."""

from ui.tui.widgets import show_info, show_separator, show_warning


async def show_user_management() -> None:
    show_info("用户管理将在 Step 4 实现。")


async def show_session_management() -> None:
    show_info("会话管理已在主菜单中接入真实功能。")


async def show_preset_management() -> None:
    show_info("预设管理将在 Step 5 实现。")


async def show_settings() -> None:
    show_info("设置功能已在主菜单中接入真实功能。")


async def show_about() -> None:
    show_separator()
    show_info("langchain-chat：基于 LangChain 的多轮会话系统教学项目。")
    show_warning("当前处于 Step 10：导出与模型切换。")
    show_separator()
