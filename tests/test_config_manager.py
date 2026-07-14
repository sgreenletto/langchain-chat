"""Tests for Step 15 multi-environment configuration loading."""

from __future__ import annotations

import copy
import os
from pathlib import Path

import pytest
from src.core import config_manager
from src.core.config_manager import ConfigError, deep_merge_config, get_config

ENV_KEYS = {
    "APP_ENV",
    "DEV_MODEL_NAME",
    "DEV_API_BASE_URL",
    "DEV_API_KEY",
    "DEV_SENTINEL",
    "TEST_MODEL_NAME",
    "TEST_API_BASE_URL",
    "TEST_API_KEY",
    "TEST_SENTINEL",
    "PROD_MODEL_NAME",
    "PROD_API_BASE_URL",
    "PROD_API_KEY",
    "PROD_MYSQL_HOST",
    "PROD_MYSQL_PORT",
    "PROD_MYSQL_USER",
    "PROD_MYSQL_PASSWORD",
    "PROD_MYSQL_DATABASE",
    "PROD_SENTINEL",
}


@pytest.fixture(autouse=True)
def isolated_config_env(monkeypatch: pytest.MonkeyPatch):
    config_manager.reset_config_cache()
    for key in ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    yield
    config_manager.reset_config_cache()
    for key in ENV_KEYS:
        os.environ.pop(key, None)


BASE_CONFIG = """
app:
  name: langchain-chat
  version: 0.1.0
  current_step: Step 15 多环境配置区分
llm:
  default_model: default
  available_models:
    - alias: default
      display_name: Base
      model: base-model
      model_env: MODEL_NAME
      api_base_url_env: API_BASE_URL
      api_key_env: API_KEY
    - alias: backup
      display_name: Backup
      model: backup-model
      api_base_url_env: API_BASE_URL
      api_key_env: API_KEY
  temperature: 0.7
  max_tokens: 2048
  timeout: 30
  max_retries: 3
storage:
  type: sqlite
  sqlite:
    database_path: data/sqlite/app.db
  mysql:
    host_env: MYSQL_HOST
    port_env: MYSQL_PORT
    user_env: MYSQL_USER
    password_env: MYSQL_PASSWORD
    database_env: MYSQL_DATABASE
    pool_min_size: 1
    pool_max_size: 5
  file:
    path: data/filestore
    encoding: utf-8
conversation:
  title_max_length: 50
export:
  dir: data/users/{username}/exports
  filename_template: "{conversation_id}_{timestamp}.{format}"
"""


def env_config(app_env: str, *, storage_type: str = "sqlite") -> str:
    prefix = app_env.upper()
    if app_env == "prod":
        mysql = """
  mysql:
    host_env: PROD_MYSQL_HOST
    port_env: PROD_MYSQL_PORT
    user_env: PROD_MYSQL_USER
    password_env: PROD_MYSQL_PASSWORD
    database_env: PROD_MYSQL_DATABASE
    pool_min_size: 2
    pool_max_size: 10
"""
    else:
        mysql = ""
    return f"""
app:
  env: {app_env}
llm:
  available_models:
    - alias: default
      display_name: {app_env} model
      model: {app_env}-model
      model_env: {prefix}_MODEL_NAME
      api_base_url_env: {prefix}_API_BASE_URL
      api_key_env: {prefix}_API_KEY
  timeout: 9
storage:
  type: {storage_type}
  sqlite:
    database_path: data/{app_env}/sqlite/app.db
{mysql.rstrip()}
  file:
    path: data/{app_env}/filestore
export:
  dir: data/{app_env}/users/{{username}}/exports
"""


def write_config_tree(root: Path) -> None:
    (root / "config.yaml").write_text(BASE_CONFIG, encoding="utf-8")
    (root / "config.dev.yaml").write_text(env_config("dev"), encoding="utf-8")
    (root / "config.test.yaml").write_text(env_config("test"), encoding="utf-8")
    (root / "config.prod.yaml").write_text(
        env_config("prod", storage_type="mysql"),
        encoding="utf-8",
    )


def use_project_root(monkeypatch: pytest.MonkeyPatch, root: Path) -> None:
    monkeypatch.setattr(config_manager, "_project_root", lambda: root)
    config_manager.reset_config_cache()


def write_env_file(root: Path, app_env: str, *, include_mysql: bool = True) -> None:
    prefix = app_env.upper()
    lines = [
        f"{prefix}_MODEL_NAME={app_env}-dotenv-model",
        f"{prefix}_API_BASE_URL=https://{app_env}.example.test/v1",
        f"{prefix}_API_KEY={app_env}-dotenv-key",
        f"{prefix}_SENTINEL={app_env}-only",
    ]
    if app_env == "prod" and include_mysql:
        lines.extend(
            [
                "PROD_MYSQL_HOST=127.0.0.1",
                "PROD_MYSQL_PORT=3306",
                "PROD_MYSQL_USER=prod_user",
                "PROD_MYSQL_PASSWORD=prod-secret-password",
                "PROD_MYSQL_DATABASE=prod_db",
            ]
        )
    (root / f".env.{app_env}").write_text("\n".join(lines), encoding="utf-8")


@pytest.mark.parametrize(
    "raw, expected",
    [(None, "dev"), (" DEV ", "dev"), ("test", "test"), ("PROD", "prod")],
)
def test_resolve_app_env_normalizes_valid_values(raw: str | None, expected: str):
    assert config_manager.resolve_app_env(raw) == expected


def test_resolve_app_env_rejects_invalid_value():
    with pytest.raises(ConfigError, match="APP_ENV"):
        config_manager.resolve_app_env("stage")


def test_default_app_env_is_dev(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    write_config_tree(tmp_path)
    use_project_root(monkeypatch, tmp_path)

    config = get_config()

    assert config.app_env == "dev"
    assert config.app.env == "dev"
    assert config.storage.sqlite.database_path == "data/dev/sqlite/app.db"


@pytest.mark.parametrize("app_env", ["dev", "test", "prod"])
def test_dev_test_prod_are_recognized(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    app_env: str,
):
    write_config_tree(tmp_path)
    write_env_file(tmp_path, app_env)
    use_project_root(monkeypatch, tmp_path)
    monkeypatch.setenv("APP_ENV", app_env)

    config = get_config()

    assert config.app_env == app_env
    assert config.app.env == app_env
    assert config.config_files == (
        tmp_path / "config.yaml",
        tmp_path / f"config.{app_env}.yaml",
    )


def test_deep_merge_rules_do_not_mutate_base():
    base = {
        "nested": {"keep": 1, "replace": {"old": True}},
        "list_value": ["base"],
        "scalar": "base",
    }
    override = {
        "nested": {"replace": "new", "add": 2},
        "list_value": ["env", "wins"],
        "scalar": "env",
        "new_key": "allowed",
    }
    original = copy.deepcopy(base)

    merged = deep_merge_config(base, override)

    assert merged == {
        "nested": {"keep": 1, "replace": "new", "add": 2},
        "list_value": ["env", "wins"],
        "scalar": "env",
        "new_key": "allowed",
    }
    assert base == original


def test_missing_environment_yaml_raises_clear_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    (tmp_path / "config.yaml").write_text(BASE_CONFIG, encoding="utf-8")
    use_project_root(monkeypatch, tmp_path)
    monkeypatch.setenv("APP_ENV", "test")

    with pytest.raises(ConfigError, match="config.test.yaml"):
        get_config()


def test_invalid_yaml_raises_clear_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    (tmp_path / "config.yaml").write_text(BASE_CONFIG, encoding="utf-8")
    (tmp_path / "config.dev.yaml").write_text("app: [", encoding="utf-8")
    use_project_root(monkeypatch, tmp_path)

    with pytest.raises(ConfigError, match="YAML"):
        get_config()


@pytest.mark.parametrize(
    ("app_env", "unexpected"),
    [
        ("dev", ["TEST_SENTINEL", "PROD_SENTINEL"]),
        ("test", ["DEV_SENTINEL", "PROD_SENTINEL"]),
        ("prod", ["DEV_SENTINEL", "TEST_SENTINEL"]),
    ],
)
def test_only_current_dotenv_file_is_loaded(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    app_env: str,
    unexpected: list[str],
):
    write_config_tree(tmp_path)
    for env_name in ("dev", "test", "prod"):
        write_env_file(tmp_path, env_name)
    use_project_root(monkeypatch, tmp_path)
    monkeypatch.setenv("APP_ENV", app_env)

    config = get_config()

    assert os.getenv(f"{app_env.upper()}_SENTINEL") == f"{app_env}-only"
    assert config.model_name == f"{app_env}-dotenv-model"
    for env_name in unexpected:
        assert os.getenv(env_name) is None


def test_process_environment_overrides_dotenv(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    write_config_tree(tmp_path)
    write_env_file(tmp_path, "dev")
    use_project_root(monkeypatch, tmp_path)
    monkeypatch.setenv("APP_ENV", "dev")
    monkeypatch.setenv("DEV_MODEL_NAME", "dev-os-model")

    config = get_config()

    assert config.model_name == "dev-os-model"


def test_dev_and_test_sqlite_paths_are_isolated(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    write_config_tree(tmp_path)
    use_project_root(monkeypatch, tmp_path)

    monkeypatch.setenv("APP_ENV", "dev")
    dev_config = get_config()
    config_manager.reset_config_cache()
    monkeypatch.setenv("APP_ENV", "test")
    test_config = get_config()

    assert dev_config.storage.sqlite.database_path == "data/dev/sqlite/app.db"
    assert test_config.storage.sqlite.database_path == "data/test/sqlite/app.db"
    assert (
        dev_config.storage.sqlite.database_path
        != test_config.storage.sqlite.database_path
    )


def test_prod_storage_is_mysql(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    write_config_tree(tmp_path)
    write_env_file(tmp_path, "prod")
    use_project_root(monkeypatch, tmp_path)
    monkeypatch.setenv("APP_ENV", "prod")

    config = get_config()

    assert config.storage.type == "mysql"
    assert config.get_mysql_config().database == "prod_db"


def test_prod_missing_mysql_config_fails_without_leaking_secret(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    write_config_tree(tmp_path)
    write_env_file(tmp_path, "prod", include_mysql=False)
    use_project_root(monkeypatch, tmp_path)
    monkeypatch.setenv("APP_ENV", "prod")
    monkeypatch.setenv("PROD_API_KEY", "super-secret-test-key")

    with pytest.raises(ConfigError) as exc_info:
        get_config()

    message = str(exc_info.value)
    assert "PROD_MYSQL_HOST" in message
    assert "super-secret-test-key" not in message


def test_switching_environment_after_cache_reset_is_isolated(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    write_config_tree(tmp_path)
    use_project_root(monkeypatch, tmp_path)

    monkeypatch.setenv("APP_ENV", "dev")
    dev_config = get_config()
    config_manager.reset_config_cache()
    monkeypatch.setenv("APP_ENV", "test")
    test_config = get_config()

    assert dev_config.app_env == "dev"
    assert test_config.app_env == "test"
