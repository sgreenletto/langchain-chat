# langchain-chat

`langchain-chat` 是一个基于 LangChain 的多轮会话系统教学项目。当前仓库位于：

```powershell
D:\project\langchain-chat
```

当前已推进到 Step 2，完成数据模型、存储接口、配置管理和可交互 TUI 骨架。

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
- LangChain（后续步骤引入）
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
└── src/
    ├── __init__.py
    ├── main.py
    ├── core/
    │   ├── __init__.py
    │   └── config_manager.py
    ├── interface/
    │   ├── __init__.py
    │   └── ui_protocol.py
    ├── models/
    │   ├── __init__.py
    │   └── schemas.py
    ├── storage/
    │   ├── __init__.py
    │   └── base.py
    └── ui/
        ├── __init__.py
        └── tui/
            ├── __init__.py
            ├── app.py
            ├── chat_view.py
            ├── menu_view.py
            └── widgets.py
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

Step 2 的重点是：

- 使用 Pydantic v2 定义五类核心数据模型。
- 使用 ABC 定义异步存储后端接口。
- 实现 `.env` 与 `config.yaml` 的配置读取和校验。
- 建立 Rich + prompt_toolkit 的 TUI 主菜单骨架。

## 当前 Step 状态

当前处于：

```text
Step 2：数据模型与 TUI 骨架
```

已建立基础工程结构、Pydantic 数据模型、异步存储接口、配置管理和 TUI 主菜单骨架。尚未实现数据库、用户管理、会话管理、预设 CRUD、多轮对话、模型切换或 LangChain 调用。

## 后续开发说明

后续步骤应在当前骨架基础上逐步扩展。新增依赖、配置加载、数据库、日志初始化、TUI 和模型调用时，应同步更新 README、AI 使用日志和验证命令记录。
