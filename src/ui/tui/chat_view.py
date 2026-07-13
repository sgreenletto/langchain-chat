"""TUI chat view for Step 7."""

from typing import Any

from langchain_core.messages import HumanMessage
from prompt_toolkit.history import InMemoryHistory
from rich.table import Table

from core.chat_engine import ChatStreamEvent, TokenUsage
from models.schemas import Preset, Session
from ui.tui.widgets import (
    console,
    read_chat_input,
    read_choice,
    show_error,
    show_info,
    show_menu,
    show_separator,
    show_success,
    show_warning,
)

CHAT_INPUT_HISTORY = InMemoryHistory()


async def start_chat(app: Any) -> None:
    """Start or continue a chat for the current user."""
    if app.current_user is None:
        show_warning("请先创建或切换用户。")
        return

    session = app.current_session
    if session is None or session.user_id != app.current_user.id:
        session = await _select_or_create_session(app)
        if session is None:
            return
        app.current_session = session

    await _chat_loop(app, session)


async def _select_or_create_session(app: Any) -> Session | None:
    sessions = await app.session_manager.list_user_sessions(app.current_user.id)
    if not sessions:
        show_info("当前用户还没有会话。")
        show_menu("开始对话", ["新建会话", "返回主菜单"])
        choice = await read_choice()
        if choice == "1":
            return await _create_new_session(app)
        return None

    _show_sessions("当前用户最近会话", sessions[:10])
    show_menu("开始对话", ["继续最近会话", "选择历史会话", "新建会话", "返回主菜单"])
    choice = await read_choice()
    match choice:
        case "1":
            return sessions[0]
        case "2":
            return await _choose_session(app, sessions)
        case "3":
            return await _create_new_session(app)
        case _:
            return None


async def _choose_session(app: Any, sessions: list[Session]) -> Session | None:
    _show_sessions("选择要继续的会话", sessions[:10])
    raw_value = await read_chat_input("请输入会话序号：", CHAT_INPUT_HISTORY)
    if raw_value is None:
        return None
    try:
        display_index = int(raw_value)
    except ValueError:
        show_error("请输入有效的会话序号。")
        return None

    if display_index < 1 or display_index > len(sessions[:10]):
        show_error(f"无效序号，请输入 1-{len(sessions[:10])}。")
        return None
    selected = sessions[display_index - 1]
    session = await app.session_manager.get_user_session(
        app.current_user.id,
        selected.id,
    )
    if session is None:
        show_error("会话不存在或不属于当前用户。")
        return None
    return session


async def _create_new_session(app: Any) -> Session | None:
    preset = await _choose_preset(app)
    preset_id = preset.id if preset else None
    session = await app.session_manager.create_session(
        user_id=app.current_user.id,
        model_name=app.config.model_name,
        preset_id=preset_id,
    )
    show_success(
        f"已创建新会话：{session.title}"
        + (f"（预设：{preset.name}）" if preset else "（不使用预设）")
    )
    return session


async def _choose_preset(app: Any) -> Preset | None:
    presets = await app.preset_manager.list_presets(app.current_user.id)
    options: list[Preset | None] = [None, *presets]
    table = Table(title="选择预设", show_header=True, header_style="bold cyan")
    table.add_column("序号", justify="right")
    table.add_column("名称")
    table.add_column("类型", justify="center")
    table.add_column("描述")
    for display_index, preset in enumerate(options, start=1):
        if preset is None:
            table.add_row(str(display_index), "不使用预设", "-", "")
            continue
        table.add_row(
            str(display_index),
            preset.name,
            "内置" if preset.is_builtin else "自定义",
            preset.description or "",
        )
    console.print(table)

    raw_value = await read_chat_input("请输入预设序号：", CHAT_INPUT_HISTORY)
    if raw_value is None:
        return None
    try:
        display_index = int(raw_value)
    except ValueError:
        show_error("请输入有效的预设序号，默认不使用预设。")
        return None
    if display_index < 1 or display_index > len(options):
        show_error("预设序号超出范围，默认不使用预设。")
        return None
    return options[display_index - 1]


async def _chat_loop(app: Any, session: Session) -> None:
    show_separator()
    show_info(f"进入会话：{session.title}")
    show_info("输入 /help 查看命令，输入 /exit 返回主菜单。")

    while True:
        raw_value = await read_chat_input("你：", CHAT_INPUT_HISTORY)
        if raw_value is None:
            show_info("已返回主菜单。")
            return
        user_input = raw_value.strip()
        if not user_input:
            show_warning("消息不能为空。")
            continue
        if user_input.startswith("/"):
            next_session = await _handle_command(app, session, user_input)
            if next_session is None:
                return
            session = next_session
            app.current_session = session
            continue

        messages = await app.session_manager.load_langchain_messages(session)
        messages.append(HumanMessage(content=user_input))
        console.print("[bold green]AI：[/bold green]", end="")
        response_parts: list[str] = []
        final_event: ChatStreamEvent | None = None
        try:
            async for event in app.chat_engine.stream(messages):
                if event.is_final:
                    final_event = event
                    continue
                response_parts.append(event.content)
                console.print(event.content, end="")
        except Exception as exc:
            console.print()
            show_error(f"LLM 调用失败：{type(exc).__name__}")
            continue
        console.print()

        ai_content = "".join(response_parts).strip()
        if not ai_content:
            show_error("LLM 未返回有效内容，本轮消息未保存。")
            continue

        usage = final_event.usage if final_event else TokenUsage()
        message_count_before = len(await app.session_manager.load_langchain_messages(
            session,
            include_system=False,
        ))
        await app.session_manager.save_user_message(session, user_input)
        _, session = await app.session_manager.save_ai_message_and_update_session(
            session=session,
            content=ai_content,
            prompt_tokens=usage.prompt_tokens if usage else None,
            completion_tokens=usage.completion_tokens if usage else None,
        )
        app.current_session = session

        if message_count_before == 0:
            title = await app.session_manager.generate_session_title(
                user_input,
                app.chat_engine,
            )
            session = await app.session_manager.update_session_title(
                app.current_user.id,
                session.id,
                title,
            )
            app.current_session = session
            show_info(f"会话标题已更新：{session.title}")

        _show_token_summary(usage, session)


async def _handle_command(app: Any, session: Session, command: str) -> Session | None:
    if command == "/exit":
        show_info("已退出当前对话。")
        return None
    if command == "/help":
        show_info("可用命令：/exit 返回主菜单；/new 新建会话；/rename 新标题；/help")
        return session
    if command == "/new":
        new_session = await _create_new_session(app)
        return new_session or session
    if command.startswith("/rename"):
        title = command.removeprefix("/rename").strip()
        if not title:
            show_warning("用法：/rename 新标题")
            return session
        try:
            updated = await app.session_manager.update_session_title(
                app.current_user.id,
                session.id,
                title,
            )
        except ValueError as exc:
            show_error(str(exc))
            return session
        show_success(f"会话标题已更新：{updated.title}")
        return updated

    show_warning("未知命令，输入 /help 查看可用命令。")
    return session


def _show_sessions(title: str, sessions: list[Session]) -> None:
    table = Table(title=title, show_header=True, header_style="bold cyan")
    table.add_column("序号", justify="right")
    table.add_column("标题")
    table.add_column("模型")
    table.add_column("Prompt Tokens", justify="right")
    table.add_column("Completion Tokens", justify="right")
    for display_index, session in enumerate(sessions, start=1):
        table.add_row(
            str(display_index),
            session.title,
            session.model_name or "-",
            str(session.total_prompt_tokens),
            str(session.total_completion_tokens),
        )
    console.print(table)


def _show_token_summary(usage: TokenUsage | None, session: Session) -> None:
    if usage is None or not usage.provided:
        show_info("本轮 Token：服务未提供。")
    else:
        prompt_tokens = usage.prompt_tokens or 0
        completion_tokens = usage.completion_tokens or 0
        total_tokens = usage.total_tokens
        total_text = f"，total={total_tokens}" if total_tokens is not None else ""
        show_info(
            "本轮 Token："
            f"prompt={prompt_tokens}，completion={completion_tokens}{total_text}"
        )
    show_info(
        "当前会话累计 Token："
        f"prompt={session.total_prompt_tokens}，"
        f"completion={session.total_completion_tokens}，"
        f"total={session.total_prompt_tokens + session.total_completion_tokens}"
    )
