"""Abstract UI protocol for terminal and future interface implementations."""

from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol


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


@dataclass(frozen=True)
class UITokenUsage:
    """UI 层展示用 Token 统计快照。

    该结构不依赖 ChatEngine 的内部结果类型，方便未来 WebUI 或对比视图
    使用同一份轻量数据契约。
    """

    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None


@dataclass(frozen=True)
class UIMessageContext:
    """未来多模型对比或 WebUI 可复用的上下文消息引用。"""

    role: Literal["system", "human", "ai"]
    content: str


@dataclass(frozen=True)
class MultiModelCompareRequest:
    """H2 多模型并行对比的输入契约，仅描述边界，不执行调用。"""

    prompt: str
    model_names: Sequence[str]
    context: Sequence[UIMessageContext] = field(default_factory=tuple)
    session_id: int | None = None


@dataclass(frozen=True)
class SingleModelCompareResult:
    """单个模型在多模型对比中的展示结果。"""

    model_name: str
    content: str = ""
    token_usage: UITokenUsage | None = None
    latency_seconds: float | None = None
    error: str | None = None


class MultiModelComparisonUI(Protocol):
    """可选 UI 能力：展示多模型对比结果。

    当前 TUI 不需要实现该协议。未来 WebUI 或专门的对比界面可以选择实现。
    """

    async def display_model_comparison(
        self,
        request: MultiModelCompareRequest,
        results: Sequence[SingleModelCompareResult],
    ) -> None:
        """Display a multi-model comparison result."""


AttachmentKind = Literal["image", "file"]


@dataclass(frozen=True)
class UIAttachmentRef:
    """H3 图文和文件输入的附件引用。

    `source` 只表示内容来源或外部引用，不要求 UI 在该层读取或解析文件。
    """

    filename: str
    mime_type: str
    size_bytes: int
    source: str
    kind: AttachmentKind = "file"


class AttachmentInputUI(Protocol):
    """可选 UI 能力：获取附件并展示附件状态。"""

    async def get_attachments(self) -> Sequence[UIAttachmentRef]:
        """Return attachments selected by the user."""

    async def display_attachment_status(
        self,
        attachment: UIAttachmentRef,
        status: str,
    ) -> None:
        """Display attachment processing status."""


@dataclass(frozen=True)
class SpeechToTextRequest:
    """H4 语音转文字请求边界。"""

    audio_format: str
    audio_source: str
    language: str | None = None


@dataclass(frozen=True)
class SpeechToTextResult:
    """H4 语音转文字结果边界。"""

    text: str = ""
    error: str | None = None


@dataclass(frozen=True)
class TextToSpeechRequest:
    """H4 文字转语音请求边界。"""

    text: str
    voice: str | None = None
    audio_format: str = "mp3"


@dataclass(frozen=True)
class TextToSpeechResult:
    """H4 文字转语音结果边界。"""

    audio_format: str
    audio_source: str | None = None
    error: str | None = None


class VoiceIOUI(Protocol):
    """可选 UI 能力：接收或播放音频。"""

    async def capture_audio(self) -> SpeechToTextRequest:
        """Capture or reference audio input."""

    async def play_audio(self, result: TextToSpeechResult) -> None:
        """Play or expose synthesized audio."""


ToolCallStatus = Literal["pending", "running", "completed", "failed", "cancelled"]


@dataclass(frozen=True)
class ToolCallRequest:
    """H5 Tool Calling 调用请求展示契约。"""

    tool_name: str
    call_id: str
    arguments: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ToolCallUpdate:
    """H5 Tool Calling 状态和结果展示契约。"""

    tool_name: str
    call_id: str
    status: ToolCallStatus
    result: Any | None = None
    error: str | None = None


class ToolCallingUI(Protocol):
    """可选 UI 能力：展示工具确认、进度和结果，不执行工具。"""

    async def confirm_tool_call(self, request: ToolCallRequest) -> bool:
        """Ask the user whether a tool call should continue."""

    async def display_tool_call_update(self, update: ToolCallUpdate) -> None:
        """Display tool call progress or result."""


class WebUIProtocol(Protocol):
    """H1 WebUI 接入边界。

    WebUI 实现类应同时实现 `AbstractUI` 的基础方法；这里保持独立
    Protocol，避免把未来 Web 服务生命周期强加给当前 TUI。
    core 层不应因此依赖 FastAPI、Flask 或任何具体 Web 框架。
    """

    async def run(self) -> None:
        """Start the WebUI event loop or server."""
