"""Step 13 SessionManager unit tests against temporary storage backends."""

from __future__ import annotations

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from src.core.chat_engine import ChatEngineResult, TokenUsage
from src.models.schemas import Preset, User

pytestmark = pytest.mark.asyncio


class FakeTitleEngine:
    async def generate(self, messages):
        self.messages = messages
        return ChatEngineResult(content='"Generated Title"', usage=TokenUsage())


async def seed_user(backend, username: str) -> User:
    return await backend.save_user(User(id=0, username=username))


async def seed_preset(backend, user_id: int) -> Preset:
    return await backend.save_preset(
        Preset(
            id=0,
            user_id=user_id,
            name=f"{user_id}-preset",
            system_prompt="System instructions.",
        )
    )


async def test_create_list_load_and_reject_foreign_session(
    session_manager,
    storage_backend,
) -> None:
    alice = await seed_user(storage_backend, "alice")
    bob = await seed_user(storage_backend, "bob")
    preset = await seed_preset(storage_backend, alice.id)

    session = await session_manager.create_session(
        alice.id,
        model_name="default",
        preset_id=preset.id,
        title="first",
    )
    await session_manager.create_session(bob.id, model_name="backup", title="other")

    assert session.user_id == alice.id
    assert session.model_name == "default"
    assert session.preset_id == preset.id
    assert await session_manager.get_session(alice.id, session.id) == session
    assert await session_manager.get_user_session(alice.id, session.id) == session
    assert await session_manager.get_user_session(bob.id, session.id) is None
    assert [item.id for item in await session_manager.list_sessions(alice.id)] == [
        session.id
    ]

    with pytest.raises(ValueError):
        await session_manager.create_session(9999, model_name="default")
    with pytest.raises(ValueError):
        await session_manager.create_session(bob.id, "default", preset_id=preset.id)
    with pytest.raises(ValueError):
        await session_manager.get_session(bob.id, session.id)


async def test_message_order_search_isolation_langchain_roles_and_tokens(
    session_manager,
    storage_backend,
) -> None:
    alice = await seed_user(storage_backend, "alice")
    bob = await seed_user(storage_backend, "bob")
    preset = await seed_preset(storage_backend, alice.id)
    session = await session_manager.create_session(
        alice.id,
        model_name="default",
        preset_id=preset.id,
    )
    bob_session = await session_manager.create_session(bob.id, model_name="default")

    first = await session_manager.save_user_message(session, "needle first")
    second = await session_manager.save_user_message(session, "needle second")
    ai_message, updated = await session_manager.save_ai_message_and_update_session(
        session,
        "needle answer",
        prompt_tokens=7,
        completion_tokens=5,
    )
    await session_manager.save_user_message(bob_session, "needle bob")

    assert updated.total_prompt_tokens == 7
    assert updated.total_completion_tokens == 5
    stored = await session_manager.get_session_messages(alice.id, session.id)
    assert [message.id for message in stored] == [first.id, second.id, ai_message.id]
    assert [message.role for message in stored] == ["human", "human", "ai"]

    search_results = await session_manager.search_messages(alice.id, "needle")
    assert [message.id for message in search_results] == [
        first.id,
        second.id,
        ai_message.id,
    ]
    assert await session_manager.search_messages(alice.id, "   ") == []
    assert [
        message.content
        for message in await session_manager.search_messages(bob.id, "needle")
    ] == ["needle bob"]

    langchain_messages = await session_manager.load_langchain_messages(updated)
    assert isinstance(langchain_messages[0], SystemMessage)
    assert isinstance(langchain_messages[1], HumanMessage)
    assert isinstance(langchain_messages[3], AIMessage)
    assert [message.content for message in langchain_messages] == [
        "System instructions.",
        "needle first",
        "needle second",
        "needle answer",
    ]


async def test_rename_model_switch_delete_and_post_delete_errors(
    session_manager,
    storage_backend,
) -> None:
    alice = await seed_user(storage_backend, "alice")
    bob = await seed_user(storage_backend, "bob")
    session = await session_manager.create_session(
        alice.id,
        model_name="default",
        title="old",
    )
    await session_manager.save_user_message(session, "content")

    renamed = await session_manager.rename_session(alice.id, session.id, "new")
    assert renamed.title == "new"
    switched = await session_manager.update_session_model(
        alice.id,
        session.id,
        "backup",
    )
    assert switched.model_name == "backup"
    assert len(await session_manager.get_session_messages(alice.id, session.id)) == 1

    with pytest.raises(ValueError):
        await session_manager.rename_session(alice.id, session.id, "   ")
    with pytest.raises(ValueError):
        await session_manager.rename_session(alice.id, session.id, "x" * 25)
    with pytest.raises(ValueError):
        await session_manager.rename_session(bob.id, session.id, "bad")
    with pytest.raises(ValueError):
        await session_manager.update_session_model(alice.id, session.id, "missing")

    deleted = await session_manager.delete_session(alice.id, session.id)
    assert deleted.id == session.id
    assert await storage_backend.get_session(session.id) is None
    assert await storage_backend.list_messages(session.id) == []
    with pytest.raises(ValueError):
        await session_manager.get_session(alice.id, session.id)
    with pytest.raises(ValueError):
        await session_manager.delete_session(alice.id, session.id)


async def test_generate_title_with_fallback_and_fake_engine(session_manager) -> None:
    assert await session_manager.generate_session_title("   ") != ""
    assert await session_manager.generate_session_title(" one   two three ") == (
        "one two three"
    )

    engine = FakeTitleEngine()
    title = await session_manager.generate_session_title("first message", engine)

    assert title == "Generated Title"
    assert isinstance(engine.messages[0], SystemMessage)
    assert isinstance(engine.messages[1], HumanMessage)


async def test_export_markdown_uses_tmp_data_dir_and_safe_filename(
    session_manager,
    storage_backend,
    test_config,
) -> None:
    alice = await seed_user(storage_backend, "alice/unsafe")
    preset = await seed_preset(storage_backend, alice.id)
    session = await session_manager.create_session(
        alice.id,
        model_name="default",
        preset_id=preset.id,
        title="bad:name/with?chars",
    )
    await session_manager.save_user_message(session, "human body")
    _, updated = await session_manager.save_ai_message_and_update_session(
        session,
        "ai body",
        prompt_tokens=2,
        completion_tokens=3,
    )

    exported = await session_manager.export_session_markdown(alice, updated.id)
    text = exported.read_text(encoding="utf-8")

    assert exported.is_file()
    assert exported.parent == (
        test_config.project_root / "data" / "users" / "alice_unsafe" / "exports"
    )
    assert "bad_name_with_chars" in exported.name
    assert "# bad:name/with?chars" in text
    assert "human body" in text
    assert "ai body" in text
    assert "Prompt Tokens" in text
    assert "Completion Tokens" in text


async def test_empty_missing_and_stale_session_errors(
    session_manager,
    storage_backend,
) -> None:
    alice = await seed_user(storage_backend, "alice")
    session = await session_manager.create_session(alice.id, model_name="default")

    assert await session_manager.get_session_messages(alice.id, session.id) == []
    assert await session_manager.load_langchain_messages(session) == []

    with pytest.raises(ValueError):
        await session_manager.get_session(alice.id, 9999)
    with pytest.raises(ValueError):
        await session_manager.get_session_messages(9999, session.id)

    await session_manager.delete_session(alice.id, session.id)
    with pytest.raises(ValueError):
        await session_manager.save_user_message(session, "stale")
    with pytest.raises(ValueError):
        await session_manager.save_ai_message_and_update_session(session, "stale", 1, 1)
