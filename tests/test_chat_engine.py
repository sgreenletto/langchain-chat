"""Unit tests for the Step 6 ChatEngine local behavior."""

import asyncio

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from src.core.chat_engine import ChatEngine, TokenUsage
from src.core.config_manager import get_config


def test_extract_usage_from_usage_metadata():
    message = AIMessage(
        content="hello",
        usage_metadata={
            "input_tokens": 3,
            "output_tokens": 4,
            "total_tokens": 7,
        },
    )

    usage = ChatEngine._extract_usage(message)

    assert usage == TokenUsage(
        prompt_tokens=3,
        completion_tokens=4,
        total_tokens=7,
    )
    assert usage.provided is True


def test_extract_usage_from_response_metadata():
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

    assert usage.prompt_tokens == 5
    assert usage.completion_tokens == 6
    assert usage.total_tokens == 11


def test_validate_messages_rejects_empty_list():
    with pytest.raises(ValueError, match="messages 不能为空"):
        ChatEngine._validate_messages([])


def test_validate_messages_accepts_base_messages():
    ChatEngine._validate_messages([HumanMessage(content="hello")])


def test_close_is_idempotent():
    engine = ChatEngine(get_config())

    async def close_twice() -> None:
        await engine.close()
        await engine.close()

    asyncio.run(close_twice())
