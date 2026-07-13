"""Step 13 ChatEngine tests using fake model boundaries."""

from __future__ import annotations

import pytest
from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    HumanMessage,
    SystemMessage,
)
from src.core.chat_engine import ChatEngine, TokenUsage
from src.core.config_manager import ConfigError


class FakeModel:
    def __init__(
        self,
        *,
        response: AIMessage | None = None,
        chunks: list[AIMessageChunk] | None = None,
        error: Exception | None = None,
        stream_error: Exception | None = None,
    ) -> None:
        self.response = response or AIMessage(
            content="full response",
            usage_metadata={
                "input_tokens": 3,
                "output_tokens": 4,
                "total_tokens": 7,
            },
        )
        self.chunks = chunks or [
            AIMessageChunk(content="one "),
            AIMessageChunk(content="two"),
            AIMessageChunk(
                content="",
                usage_metadata={
                    "input_tokens": 5,
                    "output_tokens": 6,
                    "total_tokens": 11,
                },
            ),
        ]
        self.error = error
        self.stream_error = stream_error
        self.invocations: list[list] = []
        self.stream_invocations: list[list] = []
        self.closed = False
        self.async_client = self

    async def ainvoke(self, messages):
        self.invocations.append(messages)
        if self.error is not None:
            raise self.error
        return self.response

    async def astream(self, messages):
        self.stream_invocations.append(messages)
        if self.stream_error is not None:
            raise self.stream_error
        for chunk in self.chunks:
            yield chunk

    async def close(self) -> None:
        self.closed = True


def install_fake_model(monkeypatch: pytest.MonkeyPatch, fake_model: FakeModel) -> None:
    def fake_get_model(self: ChatEngine, model_alias: str):
        self._models[model_alias] = fake_model
        return fake_model

    monkeypatch.setattr(ChatEngine, "_get_model", fake_get_model)


def test_content_and_usage_helpers() -> None:
    message = AIMessage(
        content="hello",
        response_metadata={
            "token_usage": {
                "prompt_tokens": 5,
                "completion_tokens": 6,
                "total_tokens": 11,
            }
        },
    )

    usage = ChatEngine._extract_usage(message)

    assert usage == TokenUsage(prompt_tokens=5, completion_tokens=6, total_tokens=11)
    assert ChatEngine._content_to_text("plain") == "plain"
    assert ChatEngine._content_to_text([{"text": "one"}, {"content": "two"}]) == (
        "onetwo"
    )


def test_validate_messages_rejects_empty_and_invalid_items() -> None:
    with pytest.raises(ValueError):
        ChatEngine._validate_messages([])
    with pytest.raises(TypeError):
        ChatEngine._validate_messages([object()])  # type: ignore[list-item]


@pytest.mark.asyncio
async def test_initializes_with_default_model_and_generates_response(
    test_config,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_model = FakeModel()
    install_fake_model(monkeypatch, fake_model)
    engine = ChatEngine(test_config)

    result = await engine.generate([HumanMessage(content="hello")])

    assert engine.model_alias == "default"
    assert engine.model_name == "unit-default-model"
    assert result.content == "full response"
    assert result.prompt_tokens == 3
    assert result.completion_tokens == 4
    assert fake_model.invocations[0][0].content == "hello"


@pytest.mark.asyncio
async def test_stream_yields_chunks_in_order_and_final_usage(
    test_config,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_model = FakeModel()
    install_fake_model(monkeypatch, fake_model)
    engine = ChatEngine(test_config)

    events = [event async for event in engine.stream([HumanMessage(content="go")])]

    assert [event.content for event in events] == ["one ", "two", ""]
    assert [event.is_final for event in events] == [False, False, True]
    assert events[-1].usage.prompt_tokens == 5
    assert events[-1].usage.completion_tokens == 6
    assert fake_model.stream_invocations[0][0].content == "go"


@pytest.mark.asyncio
async def test_history_and_system_prompt_are_passed_without_reordering(
    test_config,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_model = FakeModel()
    install_fake_model(monkeypatch, fake_model)
    engine = ChatEngine(test_config)
    messages = [
        SystemMessage(content="system"),
        HumanMessage(content="first"),
        AIMessage(content="previous"),
        HumanMessage(content="second"),
    ]

    await engine.generate(messages)

    assert fake_model.invocations[0] == messages


@pytest.mark.asyncio
async def test_for_model_validates_alias_and_preserves_history_inputs(
    test_config,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_model = FakeModel()
    install_fake_model(monkeypatch, fake_model)
    engine = ChatEngine(test_config)

    backup_engine = engine.for_model("backup")
    await backup_engine.generate([HumanMessage(content="after switch")])

    assert backup_engine.model_alias == "backup"
    assert backup_engine.model_name == "unit-backup-model"
    assert fake_model.invocations[-1][0].content == "after switch"
    with pytest.raises(ConfigError):
        engine.for_model("does-not-exist")


@pytest.mark.asyncio
async def test_generate_supports_per_call_model_alias(
    test_config,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_model = FakeModel()
    requested_aliases: list[str] = []

    def fake_get_model(self: ChatEngine, model_alias: str):
        requested_aliases.append(model_alias)
        self._models[model_alias] = fake_model
        return fake_model

    monkeypatch.setattr(ChatEngine, "_get_model", fake_get_model)
    engine = ChatEngine(test_config)

    await engine.generate([HumanMessage(content="hello")], model_alias="backup")

    assert requested_aliases == ["default", "backup"]


@pytest.mark.asyncio
async def test_timeout_and_stream_errors_are_raised_as_failures(
    test_config,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_model = FakeModel(error=TimeoutError("timed out"))
    install_fake_model(monkeypatch, fake_model)
    engine = ChatEngine(test_config)

    with pytest.raises(TimeoutError):
        await engine.generate([HumanMessage(content="hello")])

    stream_model = FakeModel(stream_error=RuntimeError("stream broke"))
    install_fake_model(monkeypatch, stream_model)
    stream_engine = ChatEngine(test_config)
    with pytest.raises(RuntimeError):
        [event async for event in stream_engine.stream([HumanMessage(content="go")])]


def test_get_model_delegates_timeout_and_retry_config_to_chat_openai(
    test_config,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict = {}

    class CapturingChatOpenAI:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr("src.core.chat_engine.ChatOpenAI", CapturingChatOpenAI)

    ChatEngine(test_config)

    assert captured["model"] == "unit-default-model"
    assert captured["timeout"] == 3
    assert captured["max_retries"] == 2
    assert captured["streaming"] is True
    assert captured["stream_usage"] is True


@pytest.mark.asyncio
async def test_close_is_idempotent_and_closed_engine_rejects_calls(
    test_config,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_model = FakeModel()
    install_fake_model(monkeypatch, fake_model)
    engine = ChatEngine(test_config)

    await engine.close()
    await engine.close()

    assert fake_model.closed is True
    with pytest.raises(RuntimeError):
        await engine.generate([HumanMessage(content="hello")])
