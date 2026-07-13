"""Stateless LangChain chat engine for Step 6."""

import inspect
import logging
from collections.abc import AsyncIterator, Mapping
from dataclasses import dataclass
from typing import Any

from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage
from langchain_openai import ChatOpenAI

from .config_manager import AppConfig, ModelRuntimeConfig, get_config

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TokenUsage:
    """Token usage reported by an OpenAI-compatible service."""

    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None

    @property
    def provided(self) -> bool:
        return any(
            value is not None
            for value in (
                self.prompt_tokens,
                self.completion_tokens,
                self.total_tokens,
            )
        )


@dataclass(frozen=True)
class ChatEngineResult:
    """Non-streaming chat result."""

    content: str
    usage: TokenUsage

    @property
    def prompt_tokens(self) -> int | None:
        return self.usage.prompt_tokens

    @property
    def completion_tokens(self) -> int | None:
        return self.usage.completion_tokens

    @property
    def total_tokens(self) -> int | None:
        return self.usage.total_tokens


@dataclass(frozen=True)
class ChatStreamEvent:
    """One stream event.

    `content` contains a streamed text delta. The final event sets `is_final=True`
    and carries token usage when the service provides it.
    """

    content: str = ""
    usage: TokenUsage | None = None
    is_final: bool = False


class ChatEngine:
    """Stateless OpenAI-compatible chat engine.

    The engine does not store users, sessions, or message history. Callers pass the
    full message history for every invocation.
    """

    def __init__(
        self,
        config: AppConfig | None = None,
        model_alias: str | None = None,
    ) -> None:
        self.config = config or get_config()
        self.model_alias = model_alias or self.config.default_model_alias
        self._default_model_config = self.config.get_model_config(self.model_alias)
        self.model_name = self._default_model_config.model
        self._closed = False
        self._models: dict[str, ChatOpenAI] = {}
        self._model = self._get_model(self.model_alias)

    def for_model(self, model_alias: str) -> "ChatEngine":
        """Return a stateless engine instance using one configured model alias."""
        self.config.validate_model_alias(model_alias, require_available=True)
        logger.info(
            "Chat engine model selected",
            extra={
                "model_alias": model_alias,
                "operation": "switch_model",
                "status": "ok",
            },
        )
        return ChatEngine(self.config, model_alias=model_alias)

    async def generate(
        self,
        messages: list[BaseMessage],
        model_alias: str | None = None,
    ) -> ChatEngineResult:
        """Run a non-streaming chat completion with the full message history."""
        self._ensure_open()
        self._validate_messages(messages)
        runtime_config = self._get_runtime_config(model_alias)
        model = self._get_model(runtime_config.alias)
        logger.info(
            "Starting LLM call",
            extra={
                "model_alias": runtime_config.alias,
                "model": runtime_config.model,
                "call_type": "non_stream",
                "timeout": runtime_config.timeout,
                "max_retries": runtime_config.max_retries,
            },
        )
        try:
            response = await model.ainvoke(messages)
        except Exception as exc:
            if self._is_timeout_error(exc):
                logger.warning(
                    "LLM call timed out after configured retries",
                    extra={
                        "model_alias": runtime_config.alias,
                        "model": runtime_config.model,
                        "call_type": "non_stream",
                        "timeout": runtime_config.timeout,
                        "max_retries": runtime_config.max_retries,
                        "status": "timeout",
                        "error_type": type(exc).__name__,
                    },
                )
            logger.exception(
                "LLM call failed",
                extra={
                    "model_alias": runtime_config.alias,
                    "model": runtime_config.model,
                    "call_type": "non_stream",
                    "max_retries": runtime_config.max_retries,
                    "status": "failed",
                    "error_type": type(exc).__name__,
                },
            )
            raise

        content = self._content_to_text(response.content)
        result = ChatEngineResult(
            content=content,
            usage=self._extract_usage(response),
        )
        logger.info(
            "LLM call completed",
            extra={
                "model_alias": runtime_config.alias,
                "model": runtime_config.model,
                "call_type": "non_stream",
                "status": "ok",
            },
        )
        return result

    async def stream(
        self,
        messages: list[BaseMessage],
        model_alias: str | None = None,
    ) -> AsyncIterator[ChatStreamEvent]:
        """Stream a chat completion with the full message history."""
        self._ensure_open()
        self._validate_messages(messages)
        runtime_config = self._get_runtime_config(model_alias)
        model = self._get_model(runtime_config.alias)
        logger.info(
            "Starting LLM call",
            extra={
                "model_alias": runtime_config.alias,
                "model": runtime_config.model,
                "call_type": "stream",
                "timeout": runtime_config.timeout,
                "max_retries": runtime_config.max_retries,
            },
        )
        final_usage = TokenUsage()
        try:
            async for chunk in model.astream(messages):
                usage = self._extract_usage(chunk)
                if usage.provided:
                    final_usage = usage
                content = self._content_to_text(chunk.content)
                if content:
                    yield ChatStreamEvent(content=content)
        except Exception as exc:
            if self._is_timeout_error(exc):
                logger.warning(
                    "Streaming LLM call timed out after configured retries",
                    extra={
                        "model_alias": runtime_config.alias,
                        "model": runtime_config.model,
                        "call_type": "stream",
                        "timeout": runtime_config.timeout,
                        "max_retries": runtime_config.max_retries,
                        "status": "timeout",
                        "error_type": type(exc).__name__,
                    },
                )
            logger.exception(
                "Streaming LLM call failed",
                extra={
                    "model_alias": runtime_config.alias,
                    "model": runtime_config.model,
                    "call_type": "stream",
                    "max_retries": runtime_config.max_retries,
                    "status": "failed",
                    "error_type": type(exc).__name__,
                },
            )
            raise

        logger.info(
            "Streaming LLM call completed",
            extra={
                "model_alias": runtime_config.alias,
                "model": runtime_config.model,
                "call_type": "stream",
                "status": "ok",
            },
        )
        yield ChatStreamEvent(usage=final_usage, is_final=True)

    async def close(self) -> None:
        """Close underlying client resources when available."""
        if self._closed:
            return

        for model in self._models.values():
            for attr_name in ("root_async_client", "async_client"):
                client = getattr(model, attr_name, None)
                close = getattr(client, "close", None)
                if close is None:
                    continue
                result = close()
                if inspect.isawaitable(result):
                    await result
        self._closed = True

    def _ensure_open(self) -> None:
        if self._closed:
            raise RuntimeError("ChatEngine 已关闭，不能继续发起调用。")

    @staticmethod
    def _validate_messages(messages: list[BaseMessage]) -> None:
        if not messages:
            raise ValueError("messages 不能为空，调用方必须传入完整消息历史。")
        if not all(isinstance(message, BaseMessage) for message in messages):
            raise TypeError(
                "messages 必须是 langchain_core.messages.BaseMessage 列表。"
            )

    def _get_runtime_config(self, model_alias: str | None) -> ModelRuntimeConfig:
        alias = model_alias or self.model_alias
        return self.config.get_model_config(alias, require_available=True)

    def _get_model(self, model_alias: str) -> ChatOpenAI:
        runtime_config = self.config.get_model_config(model_alias)
        model = self._models.get(runtime_config.alias)
        if model is not None:
            return model
        model = ChatOpenAI(
            model=runtime_config.model,
            api_key=runtime_config.api_key,
            base_url=runtime_config.api_base_url,
            temperature=runtime_config.temperature,
            max_completion_tokens=runtime_config.max_tokens,
            timeout=runtime_config.timeout,
            max_retries=runtime_config.max_retries,
            streaming=True,
            stream_usage=True,
        )
        self._models[runtime_config.alias] = model
        return model

    @classmethod
    def _extract_usage(cls, message: AIMessage | AIMessageChunk | Any) -> TokenUsage:
        usage_metadata = getattr(message, "usage_metadata", None)
        if isinstance(usage_metadata, Mapping):
            return cls._usage_from_mapping(usage_metadata)

        response_metadata = getattr(message, "response_metadata", None)
        if isinstance(response_metadata, Mapping):
            for key in ("token_usage", "usage"):
                token_usage = response_metadata.get(key)
                if isinstance(token_usage, Mapping):
                    return cls._usage_from_mapping(token_usage)

        additional_kwargs = getattr(message, "additional_kwargs", None)
        if isinstance(additional_kwargs, Mapping):
            token_usage = additional_kwargs.get("usage")
            if isinstance(token_usage, Mapping):
                return cls._usage_from_mapping(token_usage)

        return TokenUsage()

    @staticmethod
    def _usage_from_mapping(data: Mapping[str, Any]) -> TokenUsage:
        prompt_tokens = data.get("prompt_tokens", data.get("input_tokens"))
        completion_tokens = data.get("completion_tokens", data.get("output_tokens"))
        total_tokens = data.get("total_tokens")
        return TokenUsage(
            prompt_tokens=ChatEngine._safe_int(prompt_tokens),
            completion_tokens=ChatEngine._safe_int(completion_tokens),
            total_tokens=ChatEngine._safe_int(total_tokens),
        )

    @staticmethod
    def _safe_int(value: Any) -> int | None:
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _is_timeout_error(exc: Exception) -> bool:
        name = type(exc).__name__.lower()
        return isinstance(exc, TimeoutError) or "timeout" in name

    @classmethod
    def _content_to_text(cls, content: str | list[Any] | Any) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return "".join(cls._content_part_to_text(part) for part in content)
        return str(content)

    @staticmethod
    def _content_part_to_text(part: Any) -> str:
        if isinstance(part, str):
            return part
        if isinstance(part, Mapping):
            value = part.get("text") or part.get("content") or ""
            return str(value)
        return str(part)
