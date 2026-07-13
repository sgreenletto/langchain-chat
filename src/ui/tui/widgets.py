"""Reusable Rich widgets for the TUI skeleton."""

import asyncio
import platform

from prompt_toolkit import PromptSession
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()
prompt_session: PromptSession[str] | None = None


def show_banner() -> None:
    """Display the startup banner."""
    banner = (
        "[bold]langchain-chat[/bold]\n"
        "Step 5：预设管理\n"
        f"Python 版本：{platform.python_version()}\n"
        f"运行平台：{platform.platform()}"
    )
    console.print(Panel(banner, title="启动", border_style="cyan"))


def show_success(message: str) -> None:
    console.print(f"[green]OK[/green] {message}")


def show_error(message: str) -> None:
    console.print(f"[red]错误：[/red]{message}")


def show_warning(message: str) -> None:
    console.print(f"[yellow]提示：[/yellow]{message}")


def show_info(message: str) -> None:
    console.print(f"[cyan]信息：[/cyan]{message}")


def show_menu(title: str, options: list[str]) -> None:
    table = Table(title=title, show_header=True, header_style="bold cyan")
    table.add_column("编号", justify="center", style="bold")
    table.add_column("菜单项")

    for index, option in enumerate(options, start=1):
        table.add_row(str(index), option)

    console.print(table)


def _get_prompt_session() -> PromptSession[str]:
    global prompt_session
    if prompt_session is None:
        prompt_session = PromptSession()
    return prompt_session


async def read_text(prompt: str, default: str = "") -> str:
    display_prompt = prompt
    if default:
        display_prompt = f"{prompt}（当前：{default}，直接回车保留）："

    try:
        session = _get_prompt_session()
        value = (await session.prompt_async(display_prompt)).strip()
    except Exception:
        value = (await asyncio.to_thread(console.input, display_prompt)).strip()

    if default and not value:
        return default
    return value


async def read_choice(prompt: str = "请选择菜单编号：") -> str:
    return await read_text(prompt)


def show_separator() -> None:
    console.rule(style="cyan")
