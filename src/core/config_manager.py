"""Configuration loading and validation for langchain-chat."""

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


class ConfigError(RuntimeError):
    """Raised when application configuration cannot be loaded."""


class EnvSettings(BaseSettings):
    """Environment variables used by later steps."""

    api_base_url: str = "https://api.example.com/v1"
    api_key: str = "your_api_key_here"
    model_name: str = "your_model_name_here"
    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_user: str = "root"
    mysql_password: str = "your_mysql_password_here"
    mysql_database: str = "langchain_chat"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


class AppSection(BaseModel):
    name: str
    version: str


class AvailableModel(BaseModel):
    name: str
    provider: str
    description: str = ""


class LLMSection(BaseModel):
    default_model: str
    available_models: list[AvailableModel] = Field(default_factory=list)
    temperature: float = Field(ge=0, le=2)
    max_tokens: int = Field(gt=0)
    timeout: int = Field(gt=0)
    max_retries: int = Field(ge=0)


class SQLiteStorageSection(BaseModel):
    database_path: str


class MySQLStorageSection(BaseModel):
    host_env: str
    port_env: str
    user_env: str
    password_env: str
    database_env: str


class FileStorageSection(BaseModel):
    base_dir: str
    encoding: str = "utf-8"


class StorageSection(BaseModel):
    type: str = Field(pattern="^(sqlite|mysql|file)$")
    sqlite: SQLiteStorageSection
    mysql: MySQLStorageSection
    file: FileStorageSection


class ConversationSection(BaseModel):
    title_max_length: int = Field(gt=0)


class ExportSection(BaseModel):
    dir: str
    filename_template: str


class AppConfig(BaseModel):
    app: AppSection
    llm: LLMSection
    storage: StorageSection
    conversation: ConversationSection
    export: ExportSection
    env: EnvSettings
    project_root: Path


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ConfigError(f"配置文件不存在：{path.name}")

    try:
        with path.open("r", encoding="utf-8") as file:
            data = yaml.safe_load(file) or {}
    except yaml.YAMLError as exc:
        raise ConfigError(f"配置文件 YAML 格式错误：{path.name}") from exc
    except OSError as exc:
        raise ConfigError(f"无法读取配置文件：{path.name}") from exc

    if not isinstance(data, dict):
        raise ConfigError(f"配置文件顶层必须是映射结构：{path.name}")
    return data


@lru_cache(maxsize=1)
def get_config() -> AppConfig:
    """Load `.env` and `config.yaml`, then return a validated config object."""
    root = _project_root()
    env_path = root / ".env"
    config_path = root / "config.yaml"

    load_dotenv(env_path)
    raw_config = _load_yaml(config_path)

    try:
        env_settings = EnvSettings(_env_file=env_path if env_path.exists() else None)
        return AppConfig(
            **raw_config,
            env=env_settings,
            project_root=root,
        )
    except ValidationError as exc:
        raise ConfigError(
            "配置校验失败，请检查 config.yaml 和 .env.example 中的字段。"
        ) from exc
