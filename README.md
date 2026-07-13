# langchain-chat

`langchain-chat` 是一个基于 LangChain 的多轮会话系统教学项目。当前仓库位于：

```powershell
D:\project\langchain-chat
```

当前已推进到 Step 11，完成 MySQL 异步存储后端与存储切换验证。

## 计划功能

- 基于大模型 API 的多轮对话。
- 用户管理、会话管理和历史记录保存。
- 系统预设管理和后续用户自定义预设。
- 支持 SQLite、MySQL 和文件存储的扩展结构。
- 支持对话导出、运行日志和后续多环境配置。
- 后续引入 TUI 交互界面。

## 技术栈

- Python 3.12.13
- uv
- Pydantic v2
- PyYAML
- python-dotenv
- Rich
- prompt_toolkit
- aiosqlite
- aiomysql
- LangChain
- langchain-openai
- OpenAI SDK
- httpx
- SQLite / MySQL / 文件存储（后续步骤实现）
- Ruff、pytest（保留基础配置，后续步骤使用）

## 当前目录结构

```text
langchain-chat/
├── .env.example
├── .gitignore
├── config.yaml
├── pyproject.toml
├── README.md
├── uv.lock
├── config/
│   ├── logging.yaml
│   └── presets.yaml
├── docs/
│   └── ai_usage_log.md
├── examples/
│   ├── __init__.py
│   ├── example1_http.py
│   ├── example2_openai_sdk.py
│   └── example3_langchain.py
└── src/
    ├── __init__.py
    ├── main.py
    ├── core/
    │   ├── __init__.py
    │   ├── chat_engine.py
    │   ├── config_manager.py
    │   ├── preset_manager.py
    │   ├── session_manager.py
    │   └── user_manager.py
    ├── interface/
    │   ├── __init__.py
    │   └── ui_protocol.py
    ├── models/
    │   ├── __init__.py
    │   └── schemas.py
    ├── storage/
    │   ├── __init__.py
    │   ├── base.py
    │   ├── factory.py
    │   ├── mysql_backend.py
    │   └── sqlite_backend.py
    └── ui/
        ├── __init__.py
        └── tui/
            ├── __init__.py
            ├── app.py
            ├── chat_view.py
            ├── menu_view.py
            └── widgets.py
├── scripts/
│   ├── __init__.py
│   ├── init_db.py
│   └── test_chat_engine.py
└── tests/
    ├── __init__.py
    └── test_sqlite_backend.py
```

## 环境要求

- Windows PowerShell
- Git
- uv
- Python 3.12.13

检查 uv：

```powershell
uv --version
```

同步 Python 环境和锁文件：

```powershell
Set-Location D:\project\langchain-chat
uv sync --python 3.12.13
```

## 运行方式

查看 Python 版本：

```powershell
uv run python --version
```

以脚本方式运行：

```powershell
uv run python src/main.py
```

以模块方式运行：

```powershell
uv run python -m src.main
```

初始化当前配置的存储后端：

```powershell
uv run python scripts/init_db.py
```

默认配置使用 SQLite。切换到 MySQL 时，需要将 `config.yaml` 中
`storage.type` 改为 `mysql`，并在未提交的本地 `.env` 中配置：

```dotenv
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_mysql_password_here
MYSQL_DATABASE=langchain_chat
```

导入 ChatEngine：

```powershell
uv run python -c "from src.core.chat_engine import ChatEngine; print(ChatEngine.__name__)"
```

在本地 `.env` 配置有效 OpenAI 兼容服务后，可运行 Step 6 示例：

```powershell
uv run python -m examples.example1_http
uv run python -m examples.example2_openai_sdk
uv run python -m examples.example3_langchain
uv run python scripts/test_chat_engine.py
```

Step 10 的会话导出文件会写入当前用户目录：

```text
data/users/{username}/exports/
```

## .env.example 使用说明

`.env.example` 只保存变量模板和占位值，不保存真实 API Key、数据库密码或令牌。

后续需要本地运行真实模型或数据库时，可以由开发者自行创建未纳入版本控制的 `.env` 文件，并根据 `.env.example` 填写本机配置。

## 配置分层说明

- `.env.example`：环境变量模板，只描述需要哪些敏感配置，不保存真实密钥。
- `config.yaml`：业务配置，例如应用名称、模型注册表、生成参数、存储结构、导出路径等。
- `config/logging.yaml`：日志配置模板，后续可由 `logging.config.dictConfig()` 加载。
- `config/presets.yaml`：系统内置提示词预设，Step 1 只保存配置，不实现读取和管理。

Step 15 计划采用：

```text
最终配置 = config.yaml + config.{APP_ENV}.yaml
```

当前 Step 不创建 `config.dev.yaml`、`config.test.yaml` 或 `config.prod.yaml`，也不实现多环境加载逻辑。

## 15 个 Step 的开发方式

项目按教学步骤逐步推进。每个 Step 应只实现当前阶段要求的能力，先验证本步骤，再进入下一步。

Step 11 的重点是：

- 使用 `aiomysql` 实现 MySQL 异步存储后端。
- MySQLBackend 实现当前 `StorageBackend` 的全部抽象方法。
- `StorageFactory` 支持根据配置切换 SQLite 和 MySQL。
- `scripts/init_db.py` 根据当前配置初始化 SQLite 或 MySQL 表结构。
- MySQL 集成测试通过 `RUN_MYSQL_TESTS=1` 显式启用，默认测试不依赖外部 MySQL 服务。

## 当前 Step 状态

当前处于：

```text
Step 11  MySQL 存储后端
```

已建立基础工程结构、Pydantic 数据模型、异步存储接口、配置管理、TUI 主菜单骨架、SQLite 存储后端、MySQL 存储后端、用户管理菜单、预设管理菜单、无状态对话引擎、TUI 多轮流式对话视图、当前用户会话管理、历史消息搜索、Markdown 导出和运行时模型切换。FileBackend 留到 Step 12。

## 后续开发说明

后续步骤应在当前骨架基础上逐步扩展。新增依赖、配置加载、数据库、日志初始化、TUI 和模型调用时，应同步更新 README、AI 使用日志和验证命令记录。
