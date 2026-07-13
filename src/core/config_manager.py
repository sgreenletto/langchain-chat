"""Configuration loading and validation for langchain-chat."""

import os
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
    current_step: str = "Step 6  对话引擎"


class ModelRegistryItem(BaseModel):
    alias: str
    display_name: str
    model: str
    api_base_url_env: str = "API_BASE_URL"
    api_key_env: str = "API_KEY"
    model_env: str | None = None
    temperature: float | None = Field(default=None, ge=0, le=2)
    max_tokens: int | None = Field(default=None, gt=0)
    timeout: int | None = Field(default=None, gt=0)
    max_retries: int | None = Field(default=None, ge=0)
    provider: str = ""
    description: str = ""


class ModelRuntimeConfig(BaseModel):
    alias: str
    display_name: str
    model: str
    api_base_url: str
    api_key: str
    temperature: float
    max_tokens: int
    timeout: int
    max_retries: int
    provider: str = ""
    description: str = ""
    missing_env_vars: list[str] = Field(default_factory=list)

    @property
    def available(self) -> bool:
        return not self.missing_env_vars


class LLMSection(BaseModel):
    default_model: str
    available_models: list[ModelRegistryItem] = Field(default_factory=list)
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

    @property
    def current_step(self) -> str:
        return self.app.current_step

    @property
    def temperature(self) -> float:
        return self.llm.temperature

    @property
    def max_tokens(self) -> int:
        return self.llm.max_tokens

    @property
    def llm_timeout(self) -> int:
        return self.llm.timeout

    @property
    def llm_max_retries(self) -> int:
        return self.llm.max_retries

    @property
    def api_base_url(self) -> str:
        return self.get_model_config(self.default_model_alias).api_base_url

    @property
    def api_key(self) -> str:
        return self.get_model_config(self.default_model_alias).api_key

    @property
    def model_name(self) -> str:
        return self.get_model_config(self.default_model_alias).model

    @property
    def default_model_alias(self) -> str:
        return self.llm.default_model

    def get_model_registry(self) -> list[ModelRegistryItem]:
        """Return all configured model registry items."""
        return list(self.llm.available_models)

    def get_model_aliases(self) -> list[str]:
        """Return all configured model aliases."""
        return [model.alias for model in self.llm.available_models]

    def get_available_models(self) -> list[ModelRuntimeConfig]:
        """Return model configs whose required environment variables are present."""
        return [
            model
            for model in (
                self.get_model_config(item.alias)
                for item in self.llm.available_models
            )
            if model.available
        ]

    def get_model_config(
        self,
        model_alias: str | None = None,
        *,
        require_available: bool = False,
    ) -> ModelRuntimeConfig:
        """Return a runtime model config by alias without exposing other env vars."""
        alias = model_alias or self.default_model_alias
        item = self._get_model_item(alias)
        model_name = self._resolve_model_name(item)
        api_base_url = self._read_env(
            item.api_base_url_env,
            self.env.api_base_url if item.api_base_url_env == "API_BASE_URL" else "",
        )
        api_key = self._read_env(
            item.api_key_env,
            self.env.api_key if item.api_key_env == "API_KEY" else "",
        )
        missing_env_vars = self._missing_required_env_vars(
            item,
            model_name,
            api_base_url,
            api_key,
        )
        runtime = ModelRuntimeConfig(
            alias=item.alias,
            display_name=item.display_name,
            model=model_name,
            api_base_url=api_base_url,
            api_key=api_key,
            temperature=item.temperature
            if item.temperature is not None
            else self.llm.temperature,
            max_tokens=(
                item.max_tokens if item.max_tokens is not None else self.llm.max_tokens
            ),
            timeout=item.timeout if item.timeout is not None else self.llm.timeout,
            max_retries=item.max_retries
            if item.max_retries is not None
            else self.llm.max_retries,
            provider=item.provider,
            description=item.description,
            missing_env_vars=missing_env_vars,
        )
        if require_available and not runtime.available:
            missing = "、".join(runtime.missing_env_vars)
            raise ConfigError(f"模型 '{alias}' 缺少必要环境变量：{missing}")
        return runtime

    def get_default_model_config(
        self,
        *,
        require_available: bool = False,
    ) -> ModelRuntimeConfig:
        """Return the system default model config."""
        return self.get_model_config(
            self.default_model_alias,
            require_available=require_available,
        )

    def validate_model_alias(
        self,
        model_alias: str,
        *,
        require_available: bool = True,
    ) -> ModelRuntimeConfig:
        """Validate that a model alias exists and is optionally usable."""
        return self.get_model_config(
            model_alias,
            require_available=require_available,
        )

    def _get_model_item(self, model_alias: str) -> ModelRegistryItem:
        for item in self.llm.available_models:
            if item.alias == model_alias:
                return item
        raise ConfigError(f"模型别名不存在：{model_alias}")

    def _resolve_model_name(self, item: ModelRegistryItem) -> str:
        if item.model_env:
            value = self._read_env(item.model_env, "")
            if not self._is_placeholder(value):
                return value
        if item.alias == self.default_model_alias and not self._is_placeholder(
            self.env.model_name
        ):
            return self.env.model_name
        return item.model

    @staticmethod
    def _read_env(env_name: str, fallback: str) -> str:
        return os.getenv(env_name, fallback).strip()

    @classmethod
    def _missing_required_env_vars(
        cls,
        item: ModelRegistryItem,
        model_name: str,
        api_base_url: str,
        api_key: str,
    ) -> list[str]:
        missing: list[str] = []
        if cls._is_placeholder(model_name):
            missing.append(item.model_env or "MODEL_NAME")
        if cls._is_placeholder(api_base_url):
            missing.append(item.api_base_url_env)
        if cls._is_placeholder(api_key):
            missing.append(item.api_key_env)
        return missing

    @staticmethod
    def _is_placeholder(value: str | None) -> bool:
        if value is None:
            return True
        stripped = value.strip()
        return stripped.startswith("your_") or stripped in {
            "",
            "https://api.example.com/v1",
            "your_api_key_here",
            "your_model_name_here",
        }


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
        config = AppConfig(
            **raw_config,
            env=env_settings,
            project_root=root,
        )
        config.get_default_model_config()
        return config
    except ValidationError as exc:
        raise ConfigError(
            "配置校验失败，请检查 config.yaml 和 .env.example 中的字段。"
        ) from exc
