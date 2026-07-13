# langchain-chat

`langchain-chat` 是一个基于 LangChain 的多轮会话系统教学项目。当前仓库位于：

```powershell
D:\project\langchain-chat
```

当前已推进到 Step 7，完成会话管理业务层与 TUI 多轮流式对话视图对接。

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

初始化 SQLite 数据库并运行冒烟测试：

```powershell
uv run python scripts/init_db.py
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

## .env.example 使用说明

`.env.example` 只保存变量模板和占位值，不保存真实 API Key、数据库密码或令牌。

后续需要本地运行真实模型或数据库时，可以由开发者自行创建未纳入版本控制的 `.env` 文件，并根据 `.env.example` 填写本机配置。

## 配置分层说明

- `.env.example`：环境变量模板，只描述需要哪些敏感配置，不保存真实密钥。
- `config.yaml`：业务配置，例如应用名称、模型参数、存储结构、导出路径等。
- `config/logging.yaml`：日志配置模板，后续可由 `logging.config.dictConfig()` 加载。
- `config/presets.yaml`：系统内置提示词预设，Step 1 只保存配置，不实现读取和管理。

Step 15 计划采用：

```text
最终配置 = config.yaml + config.{APP_ENV}.yaml
```

当前 Step 不创建 `config.dev.yaml`、`config.test.yaml` 或 `config.prod.yaml`，也不实现多环境加载逻辑。

## 15 个 Step 的开发方式

项目按教学步骤逐步推进。每个 Step 应只实现当前阶段要求的能力，先验证本步骤，再进入下一步。

Step 7 的重点是：

- 使用 `SessionManager` 封装会话创建、消息保存、历史加载和标题更新。
- 将 Step 6 的无状态 `ChatEngine` 接入 TUI 对话视图。
- 支持预设选择、多轮上下文、流式回复、Token 展示和输入历史。
- 支持 `/help`、`/rename`、`/new`、`/exit` 基础命令。

## 当前 Step 状态

当前处于：

```text
Step 7  对话视图
```

已建立基础工程结构、Pydantic 数据模型、异步存储接口、配置管理、TUI 主菜单骨架、SQLite 存储后端、用户管理菜单、预设管理菜单、无状态对话引擎和 TUI 多轮流式对话视图。完整会话列表、重命名和删除管理留到 Step 8。

## 后续开发说明

后续步骤应在当前骨架基础上逐步扩展。新增依赖、配置加载、数据库、日志初始化、TUI 和模型调用时，应同步更新 README、AI 使用日志和验证命令记录。
