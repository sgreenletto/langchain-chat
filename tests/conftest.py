"""Shared pytest fixtures for Step 13 core module tests."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest
import pytest_asyncio
from src.core.config_manager import AppConfig, EnvSettings
from src.core.session_manager import SessionManager
from src.core.user_manager import UserManager
from src.models.schemas import Message, Preset, Session, User, UserConfig
from src.storage.file_backend import FileBackend
from src.storage.sqlite_backend import SQLiteBackend


@pytest.fixture
def test_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> AppConfig:
    """Return an isolated app config that never reads the real .env file."""

    monkeypatch.setenv("TEST_MODEL_NAME", "unit-default-model")
    monkeypatch.setenv("TEST_API_BASE_URL", "https://unit.test/v1")
    monkeypatch.setenv("TEST_API_KEY", "unit-test-api-key")
    monkeypatch.setenv("TEST_BACKUP_MODEL_NAME", "unit-backup-model")
    monkeypatch.setenv("TEST_BACKUP_API_BASE_URL", "https://backup.unit.test/v1")
    monkeypatch.setenv("TEST_BACKUP_API_KEY", "unit-backup-api-key")
    monkeypatch.delenv("TEST_MISSING_API_BASE_URL", raising=False)
    monkeypatch.delenv("TEST_MISSING_API_KEY", raising=False)

    return AppConfig(
        app={
            "name": "langchain-chat",
            "version": "0.1.0",
            "current_step": "Step 13 core module tests",
        },
        llm={
            "default_model": "default",
            "available_models": [
                {
                    "alias": "default",
                    "display_name": "Default",
                    "model": "placeholder-default",
                    "model_env": "TEST_MODEL_NAME",
                    "api_base_url_env": "TEST_API_BASE_URL",
                    "api_key_env": "TEST_API_KEY",
                    "temperature": 0.2,
                    "max_tokens": 128,
                    "timeout": 3,
                    "max_retries": 2,
                },
                {
                    "alias": "backup",
                    "display_name": "Backup",
                    "model": "placeholder-backup",
                    "model_env": "TEST_BACKUP_MODEL_NAME",
                    "api_base_url_env": "TEST_BACKUP_API_BASE_URL",
                    "api_key_env": "TEST_BACKUP_API_KEY",
                    "temperature": 0.4,
                    "max_tokens": 256,
                    "timeout": 5,
                    "max_retries": 1,
                },
                {
                    "alias": "missing",
                    "display_name": "Missing",
                    "model": "missing-model",
                    "api_base_url_env": "TEST_MISSING_API_BASE_URL",
                    "api_key_env": "TEST_MISSING_API_KEY",
                },
            ],
            "temperature": 0.7,
            "max_tokens": 1024,
            "timeout": 10,
            "max_retries": 3,
        },
        storage={
            "type": "sqlite",
            "sqlite": {"database_path": str(tmp_path / "unused.db")},
            "mysql": {
                "host_env": "MYSQL_HOST",
                "port_env": "MYSQL_PORT",
                "user_env": "MYSQL_USER",
                "password_env": "MYSQL_PASSWORD",
                "database_env": "MYSQL_DATABASE",
                "pool_min_size": 1,
                "pool_max_size": 2,
            },
            "file": {
                "path": str(tmp_path / "filestore"),
                "encoding": "utf-8",
            },
        },
        conversation={"title_max_length": 20},
        export={
            "dir": "data/users/{username}/exports",
            "filename_template": "{conversation_id}_{timestamp}.{format}",
        },
        env=EnvSettings(
            _env_file=None,
            api_base_url="https://unit.test/v1",
            api_key="unit-test-api-key",
            model_name="unit-default-model",
        ),
        project_root=tmp_path,
    )


@pytest.fixture(autouse=True)
def patch_config_loaders(
    test_config: AppConfig,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Patch module-level get_config references so tests do not read real config."""

    import src.storage.file_backend as src_file_backend
    import src.storage.sqlite_backend as src_sqlite_backend

    monkeypatch.setattr(src_file_backend, "get_config", lambda: test_config)
    monkeypatch.setattr(src_sqlite_backend, "get_config", lambda: test_config)

    try:
        import storage.file_backend as file_backend
        import storage.sqlite_backend as sqlite_backend
    except ImportError:
        return

    monkeypatch.setattr(file_backend, "get_config", lambda: test_config)
    monkeypatch.setattr(sqlite_backend, "get_config", lambda: test_config)


@pytest_asyncio.fixture
async def sqlite_backend(tmp_path: Path) -> SQLiteBackend:
    backend = SQLiteBackend(tmp_path / "sqlite" / "app.db")
    await backend.initialize()
    try:
        yield backend
    finally:
        await backend.close()


@pytest_asyncio.fixture
async def file_backend(tmp_path: Path) -> FileBackend:
    backend = FileBackend(tmp_path / "filestore")
    await backend.initialize()
    try:
        yield backend
    finally:
        await backend.close()


@pytest_asyncio.fixture(params=["sqlite", "file"])
async def storage_backend(
    request: pytest.FixtureRequest,
    tmp_path: Path,
) -> SQLiteBackend | FileBackend:
    if request.param == "sqlite":
        backend: SQLiteBackend | FileBackend = SQLiteBackend(
            tmp_path / "storage_contract" / "app.db"
        )
    else:
        backend = FileBackend(tmp_path / "storage_contract" / "filestore")

    await backend.initialize()
    try:
        yield backend
    finally:
        await backend.close()


@pytest.fixture
def make_user() -> Callable[..., User]:
    def factory(
        username: str = "alice",
        *,
        user_id: int = 0,
        default_model: str | None = None,
        default_preset_id: int | None = None,
    ) -> User:
        return User(
            id=user_id,
            username=username,
            default_model=default_model,
            default_preset_id=default_preset_id,
        )

    return factory


@pytest.fixture
def make_session() -> Callable[..., Session]:
    def factory(
        user_id: int,
        *,
        session_id: int = 0,
        title: str = "session",
        model_name: str | None = "default",
        preset_id: int | None = None,
    ) -> Session:
        return Session(
            id=session_id,
            user_id=user_id,
            title=title,
            model_name=model_name,
            preset_id=preset_id,
        )

    return factory


@pytest.fixture
def make_message() -> Callable[..., Message]:
    def factory(
        session_id: int,
        *,
        message_id: int = 0,
        role: str = "human",
        content: str = "hello",
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
    ) -> Message:
        return Message(
            id=message_id,
            session_id=session_id,
            role=role,  # type: ignore[arg-type]
            content=content,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )

    return factory


@pytest.fixture
def make_preset() -> Callable[..., Preset]:
    def factory(
        *,
        preset_id: int = 0,
        user_id: int | None = None,
        name: str = "preset",
        description: str = "",
        system_prompt: str = "You are helpful.",
        is_builtin: bool = False,
    ) -> Preset:
        return Preset(
            id=preset_id,
            user_id=user_id,
            name=name,
            description=description,
            system_prompt=system_prompt,
            is_builtin=is_builtin,
        )

    return factory


@pytest.fixture
def make_user_config() -> Callable[..., UserConfig]:
    def factory(
        user_id: int,
        *,
        config_id: int = 0,
        key: str = "theme",
        value: str = "dark",
    ) -> UserConfig:
        return UserConfig(id=config_id, user_id=user_id, key=key, value=value)

    return factory


@pytest.fixture
def user_manager(storage_backend: SQLiteBackend | FileBackend, test_config: AppConfig):
    return UserManager(storage_backend, config=test_config)


@pytest.fixture
def session_manager(
    storage_backend: SQLiteBackend | FileBackend,
    test_config: AppConfig,
):
    return SessionManager(storage_backend, config=test_config)
