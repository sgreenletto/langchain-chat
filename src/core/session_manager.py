"""Session management business layer."""

import asyncio
import logging
import re
from datetime import datetime
from pathlib import Path

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

try:
    from ..models.schemas import Message, Preset, Session, User, utc_now
    from ..storage.base import StorageBackend
    from .chat_engine import ChatEngine
    from .config_manager import AppConfig, ConfigError, get_config
except ImportError:
    from core.chat_engine import ChatEngine
    from core.config_manager import AppConfig, ConfigError, get_config
    from models.schemas import Message, Preset, Session, User, utc_now
    from storage.base import StorageBackend

logger = logging.getLogger(__name__)


class SessionManager:
    """Manage chat sessions and persisted messages."""

    def __init__(
        self,
        backend: StorageBackend,
        title_max_length: int | None = None,
        config: AppConfig | None = None,
    ) -> None:
        self.backend = backend
        self.config = config or get_config()
        self.title_max_length = (
            title_max_length or self.config.conversation.title_max_length
        )

    async def create_session(
        self,
        user_id: int,
        model_name: str,
        preset_id: int | None = None,
        title: str = "新会话",
    ) -> Session:
        """Create a session for a user."""
        await self._require_user(user_id)
        if preset_id is not None:
            await self._require_visible_preset(user_id, preset_id)
        saved = await self.backend.save_session(
            Session(
                id=0,
                user_id=user_id,
                title=title,
                model_name=model_name,
                preset_id=preset_id,
            )
        )
        logger.info(
            "Session created",
            extra={
                "user_id": user_id,
                "session_id": saved.id,
                "model": model_name,
                "operation": "create_session",
                "status": "ok",
            },
        )
        return saved

    async def list_sessions(self, user_id: int) -> list[Session]:
        """List sessions owned by a user."""
        await self._require_user(user_id)
        sessions = await self.backend.list_sessions(user_id)
        logger.info(
            "User sessions listed",
            extra={"user_id": user_id, "operation": "list_sessions", "status": "ok"},
        )
        return sessions

    async def list_user_sessions(self, user_id: int) -> list[Session]:
        """Backward-compatible alias for listing user sessions."""
        return await self.list_sessions(user_id)

    async def get_session(self, user_id: int, session_id: int) -> Session:
        """Return a session after validating ownership."""
        return await self._require_session_owner(user_id, session_id)

    async def get_session_messages(
        self,
        user_id: int,
        session_id: int,
    ) -> list[Message]:
        """Return messages for a user-owned session in chronological order."""
        session = await self._require_session_owner(user_id, session_id)
        messages = await self.backend.list_messages(session.id)
        logger.info(
            "Session messages loaded",
            extra={
                "user_id": user_id,
                "session_id": session.id,
                "operation": "load_session_messages",
                "status": "ok",
            },
        )
        return messages

    async def search_messages(self, user_id: int, keyword: str) -> list[Message]:
        """Search messages for one user after validating input."""
        await self._require_user(user_id)
        normalized_keyword = keyword.strip()
        if not normalized_keyword:
            return []
        results = await self.backend.search_messages(user_id, normalized_keyword)
        logger.info(
            "Messages searched",
            extra={"user_id": user_id, "operation": "search_messages", "status": "ok"},
        )
        return results

    async def get_user_session(self, user_id: int, session_id: int) -> Session | None:
        """Return a session only when it belongs to the user."""
        try:
            return await self.get_session(user_id, session_id)
        except ValueError:
            return None

    async def get_recent_session(self, user_id: int) -> Session | None:
        """Return the user's most recently updated session."""
        sessions = await self.list_user_sessions(user_id)
        return sessions[0] if sessions else None

    async def get_session_preset(self, session: Session) -> Preset | None:
        """Return the preset selected by a session."""
        if session.preset_id is None:
            return None
        return await self.backend.get_preset_by_id(session.preset_id)

    async def save_user_message(self, session: Session, content: str) -> Message:
        """Persist one human message."""
        session = await self._require_session_owner(session.user_id, session.id)
        return await self.backend.save_message(
            Message(id=0, session_id=session.id, role="human", content=content)
        )

    async def save_ai_message_and_update_session(
        self,
        session: Session,
        content: str,
        prompt_tokens: int | None,
        completion_tokens: int | None,
    ) -> tuple[Message, Session]:
        """Persist one AI message and update cumulative session token counts."""
        session = await self._require_session_owner(session.user_id, session.id)
        prompt_count = prompt_tokens or 0
        completion_count = completion_tokens or 0
        message = await self.backend.save_message(
            Message(
                id=0,
                session_id=session.id,
                role="ai",
                content=content,
                prompt_tokens=prompt_count,
                completion_tokens=completion_count,
            )
        )
        updated = Session(
            id=session.id,
            user_id=session.user_id,
            title=session.title,
            model_name=session.model_name,
            preset_id=session.preset_id,
            total_prompt_tokens=session.total_prompt_tokens + prompt_count,
            total_completion_tokens=session.total_completion_tokens + completion_count,
            created_at=session.created_at,
            updated_at=utc_now(),
        )
        saved_session = await self.backend.save_session(updated)
        return message, saved_session

    async def load_langchain_messages(
        self,
        session: Session,
        include_system: bool = True,
    ) -> list[BaseMessage]:
        """Load persisted messages in chronological order as LangChain messages."""
        session = await self._require_session_owner(session.user_id, session.id)
        result: list[BaseMessage] = []
        has_system = False
        if include_system:
            preset = await self.get_session_preset(session)
            if preset is not None and preset.system_prompt.strip():
                result.append(SystemMessage(content=preset.system_prompt.strip()))
                has_system = True

        for message in await self.backend.list_messages(session.id):
            if message.role == "system":
                if has_system:
                    continue
                result.insert(0, SystemMessage(content=message.content))
                has_system = True
                continue
            result.append(self._message_to_langchain(message))
        return result

    async def generate_session_title(
        self,
        first_user_message: str,
        chat_engine: ChatEngine | None = None,
    ) -> str:
        """Generate a short title; fall back to the first user message."""
        fallback = self._fallback_title(first_user_message)
        if chat_engine is None:
            return fallback

        try:
            result = await chat_engine.generate(
                [
                    SystemMessage(
                        content="请为用户的第一句话生成不超过15字的会话标题。"
                    ),
                    HumanMessage(content=first_user_message),
                ]
            )
        except Exception:
            return fallback

        title = result.content.strip().strip("\"'“”‘’")
        return title[:30] if title else fallback

    async def update_session_title(
        self,
        user_id: int,
        session_id: int,
        title: str,
    ) -> Session:
        """Update a session title after validating ownership."""
        normalized_title = self._validate_title(title)
        session = await self._require_session_owner(user_id, session_id)
        updated = Session(
            id=session.id,
            user_id=session.user_id,
            title=normalized_title,
            model_name=session.model_name,
            preset_id=session.preset_id,
            total_prompt_tokens=session.total_prompt_tokens,
            total_completion_tokens=session.total_completion_tokens,
            created_at=session.created_at,
            updated_at=utc_now(),
        )
        saved = await self.backend.save_session(updated)
        logger.info(
            "Session renamed",
            extra={
                "user_id": user_id,
                "session_id": session_id,
                "operation": "rename_session",
                "status": "ok",
            },
        )
        return saved

    async def rename_session(
        self,
        user_id: int,
        session_id: int,
        title: str,
    ) -> Session:
        """Rename a session after validating ownership and title."""
        return await self.update_session_title(user_id, session_id, title)

    async def delete_session(self, user_id: int, session_id: int) -> Session:
        """Delete a session after validating ownership."""
        session = await self._require_session_owner(user_id, session_id)
        deleted = await self.backend.delete_session(session.id)
        if not deleted:
            logger.error(
                "Session delete failed",
                extra={
                    "user_id": user_id,
                    "session_id": session.id,
                    "operation": "delete_session",
                    "status": "failed",
                },
            )
            raise ValueError("删除会话失败。")
        logger.info(
            "Session deleted",
            extra={
                "user_id": user_id,
                "session_id": session.id,
                "operation": "delete_session",
                "status": "ok",
            },
        )
        return session

    async def update_session_model(
        self,
        user_id: int,
        session_id: int,
        model_alias: str,
    ) -> Session:
        """Switch a user-owned session to a configured available model."""
        try:
            runtime_config = self.config.validate_model_alias(
                model_alias.strip(),
                require_available=True,
            )
        except ConfigError as exc:
            raise ValueError(str(exc)) from exc
        session = await self._require_session_owner(user_id, session_id)
        updated = Session(
            id=session.id,
            user_id=session.user_id,
            title=session.title,
            model_name=runtime_config.alias,
            preset_id=session.preset_id,
            total_prompt_tokens=session.total_prompt_tokens,
            total_completion_tokens=session.total_completion_tokens,
            created_at=session.created_at,
            updated_at=utc_now(),
        )
        saved = await self.backend.save_session(updated)
        logger.info(
            "Session model updated",
            extra={
                "user_id": user_id,
                "session_id": session_id,
                "model": saved.model_name,
                "operation": "update_session_model",
                "status": "ok",
            },
        )
        return saved

    async def export_session_markdown(
        self,
        user: User,
        session_id: int,
    ) -> Path:
        """Export one user-owned session to a Markdown file."""
        session = await self._require_session_owner(user.id, session_id)
        messages = await self.backend.list_messages(session.id)
        preset = await self.get_session_preset(session)
        export_dir = self._build_export_dir(user.username)
        filename = await self._build_unique_export_filename(export_dir, session.title)
        markdown = self._build_markdown(user, session, preset, messages)

        try:
            await asyncio.to_thread(export_dir.mkdir, parents=True, exist_ok=True)
            await asyncio.to_thread(filename.write_text, markdown, "utf-8")
        except OSError as exc:
            logger.exception(
                "Session export failed",
                extra={
                    "user_id": user.id,
                    "session_id": session_id,
                    "operation": "export_session",
                    "status": "failed",
                    "error_type": type(exc).__name__,
                },
            )
            raise
        logger.info(
            "Session exported",
            extra={
                "user_id": user.id,
                "session_id": session_id,
                "operation": "export_session",
                "status": "ok",
                "path": str(filename),
            },
        )
        return filename

    async def _require_user(self, user_id: int) -> None:
        if await self.backend.get_user_by_id(user_id) is None:
            raise ValueError("用户不存在。")

    async def _require_session_owner(self, user_id: int, session_id: int) -> Session:
        session = await self.backend.get_session(session_id)
        if session is None or session.user_id != user_id:
            raise ValueError("会话不存在或不属于当前用户。")
        return session

    async def _require_visible_preset(self, user_id: int, preset_id: int) -> None:
        preset = await self.backend.get_preset_by_id(preset_id)
        if preset is None:
            raise ValueError("预设不存在。")
        if preset.user_id is not None and preset.user_id != user_id:
            raise ValueError("不能使用其他用户的自定义预设。")

    @staticmethod
    def _message_to_langchain(message: Message) -> BaseMessage:
        match message.role:
            case "human":
                return HumanMessage(content=message.content)
            case "ai":
                return AIMessage(content=message.content)
            case "system":
                return SystemMessage(content=message.content)
        raise ValueError(f"未知消息角色：{message.role}")

    @staticmethod
    def _fallback_title(content: str) -> str:
        normalized = " ".join(content.strip().split())
        if not normalized:
            return "新会话"
        return normalized[:30]

    def _validate_title(self, title: str) -> str:
        normalized_title = title.strip()
        if not normalized_title:
            raise ValueError("会话标题不能为空。")
        if len(normalized_title) > self.title_max_length:
            raise ValueError(f"会话标题不能超过 {self.title_max_length} 个字符。")
        return normalized_title

    def _build_export_dir(self, username: str) -> Path:
        safe_username = self._safe_filename(username, fallback="user")
        relative_dir = self.config.export.dir.format(username=safe_username)
        export_dir = (self.config.project_root / relative_dir).resolve()
        data_root = (self.config.project_root / "data").resolve()
        if not export_dir.is_relative_to(data_root):
            raise ValueError("导出目录配置不安全，不能位于 data 目录之外。")
        return export_dir

    async def _build_unique_export_filename(
        self,
        export_dir: Path,
        title: str,
    ) -> Path:
        safe_title = self._safe_filename(title, fallback="session")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = export_dir / f"{safe_title}_{timestamp}.md"
        if not filename.exists():
            return filename

        counter = 2
        while True:
            candidate = export_dir / f"{safe_title}_{timestamp}_{counter}.md"
            if not candidate.exists():
                return candidate
            counter += 1

    def _build_markdown(
        self,
        user: User,
        session: Session,
        preset: Preset | None,
        messages: list[Message],
    ) -> str:
        model_text = session.model_name or self.config.default_model_alias
        preset_text = preset.name if preset else "无预设"
        total_tokens = session.total_prompt_tokens + session.total_completion_tokens
        lines = [
            f"# {self._markdown_inline(session.title)}",
            "",
            f"- 用户：{self._markdown_inline(user.username)}",
            f"- 模型：{self._markdown_inline(model_text)}",
            f"- 预设：{self._markdown_inline(preset_text)}",
            f"- 创建时间：{session.created_at.isoformat()}",
            f"- 最后更新时间：{session.updated_at.isoformat()}",
            f"- Prompt Tokens：{session.total_prompt_tokens}",
            f"- Completion Tokens：{session.total_completion_tokens}",
            f"- Total Tokens：{total_tokens}",
            "",
            "## 消息记录",
            "",
        ]
        if not messages:
            lines.append("该会话还没有任何消息。")
            lines.append("")
            return "\n".join(lines)

        for index, message in enumerate(messages, start=1):
            role_name = self._display_message_role(message.role)
            lines.extend(
                [
                    f"### {index}. {role_name}",
                    "",
                    f"- 时间：{message.created_at.isoformat()}",
                    f"- Prompt Tokens：{message.prompt_tokens}",
                    f"- Completion Tokens：{message.completion_tokens}",
                    "",
                    self._markdown_code_block(message.content),
                    "",
                ]
            )
        return "\n".join(lines)

    @staticmethod
    def _display_message_role(role: str) -> str:
        return {
            "system": "System",
            "human": "Human",
            "ai": "AI",
        }.get(role, role)

    @staticmethod
    def _markdown_inline(value: str) -> str:
        return value.replace("\n", " ").strip()

    @staticmethod
    def _markdown_code_block(content: str) -> str:
        backtick_runs = [len(match.group(0)) for match in re.finditer(r"`+", content)]
        fence_length = max([3, *(length + 1 for length in backtick_runs)])
        fence = "`" * fence_length
        return f"{fence}\n{content}\n{fence}"

    @staticmethod
    def _safe_filename(value: str, fallback: str) -> str:
        normalized = value.strip().replace("\\", "_").replace("/", "_")
        normalized = re.sub(r'[<>:"|?*\x00-\x1f]', "_", normalized)
        normalized = re.sub(r"\s+", "_", normalized)
        normalized = normalized.strip("._ ")
        if not normalized or normalized in {".", ".."}:
            normalized = fallback
        return normalized[:80]
