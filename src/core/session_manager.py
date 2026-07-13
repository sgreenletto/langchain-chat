"""Session management business layer for Step 7."""

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

try:
    from ..models.schemas import Message, Preset, Session, utc_now
    from ..storage.base import StorageBackend
    from .chat_engine import ChatEngine
except ImportError:
    from core.chat_engine import ChatEngine
    from models.schemas import Message, Preset, Session, utc_now
    from storage.base import StorageBackend


class SessionManager:
    """Manage chat sessions and persisted messages."""

    def __init__(self, backend: StorageBackend) -> None:
        self.backend = backend

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
        return await self.backend.save_session(
            Session(
                id=0,
                user_id=user_id,
                title=title,
                model_name=model_name,
                preset_id=preset_id,
            )
        )

    async def list_user_sessions(self, user_id: int) -> list[Session]:
        """List sessions owned by a user."""
        await self._require_user(user_id)
        return await self.backend.list_sessions(user_id)

    async def get_user_session(self, user_id: int, session_id: int) -> Session | None:
        """Return a session only when it belongs to the user."""
        session = await self.backend.get_session(session_id)
        if session is None or session.user_id != user_id:
            return None
        return session

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
                    SystemMessage(content="请为用户的第一句话生成不超过15字的会话标题。"),
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
        normalized_title = title.strip()
        if not normalized_title:
            raise ValueError("会话标题不能为空。")
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
        return await self.backend.save_session(updated)

    async def _require_user(self, user_id: int) -> None:
        if await self.backend.get_user_by_id(user_id) is None:
            raise ValueError("用户不存在。")

    async def _require_session_owner(self, user_id: int, session_id: int) -> Session:
        session = await self.get_user_session(user_id, session_id)
        if session is None:
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
