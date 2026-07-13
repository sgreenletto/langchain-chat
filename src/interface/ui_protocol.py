"""Abstract UI protocol for terminal and future interface implementations."""

from abc import ABC, abstractmethod


class AbstractUI(ABC):
    """Common async interface for UI implementations."""

    @abstractmethod
    async def display_message(self, message: str) -> None:
        """Display a normal message."""

    @abstractmethod
    async def get_user_input(self, prompt: str) -> str:
        """Read user input."""

    @abstractmethod
    async def display_menu(self, title: str, options: list[str]) -> None:
        """Display a menu."""

    @abstractmethod
    async def display_error(self, message: str) -> None:
        """Display an error message."""

    @abstractmethod
    async def display_info(self, message: str) -> None:
        """Display an informational message."""
