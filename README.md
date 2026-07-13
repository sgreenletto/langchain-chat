# langchain-chat

`langchain-chat` 是一个基于 LangChain 的多用户、多会话 TUI Chatbot，也是按步骤构建的工程化教学项目。

当前进度：`Step 14 README、架构文档与扩展预留`。

## 主要功能

- 多轮对话：会话历史会按用户和会话保存，并在继续对话时重新加载上下文。
- 流式输出：ChatEngine 使用 LangChain / OpenAI 兼容接口进行异步流式响应。
- 多用户隔离：用户、会话、消息、自定义预设和用户配置按 `user_id` 隔离。
- 会话管理：支持创建、加载、重命名、删除和查看历史会话。
- Prompt 预设：支持系统内置预设和用户自定义预设。
- 历史搜索：按当前用户范围搜索历史消息，避免跨用户返回数据。
- Markdown 导出：将会话导出到当前用户的导出目录。
- 模型切换：支持用户默认模型和会话运行时模型切换。
- 可插拔存储：支持 SQLite、MySQL 和 JSON 文件三种后端。
- 结构化日志：控制台日志面向开发者，文件日志为 JSONL。
- 自动化测试：核心模块使用 pytest，默认不依赖真实 LLM、互联网或 MySQL 服务。

## 技术栈

- Python `>=3.10,<3.13`
- uv
- Pydantic v2 / pydantic-settings
- LangChain / langchain-openai
- OpenAI SDK / httpx
- Rich / prompt-toolkit
- aiosqlite / aiomysql
- PyYAML / python-dotenv
- pytest / pytest-asyncio / pytest-cov
- Ruff

## 系统要求

- Python 3.10 到 3.12。当前教学环境使用 Python 3.12。
- uv，用于依赖同步、运行命令和锁文件管理。
- MySQL 仅在 `storage.type=mysql` 或显式运行 MySQL 集成测试时需要。

## 目录结构

```text
langchain-chat/
├── .env.example
├── config.yaml
├── pyproject.toml
├── uv.lock
├── README.md
├── config/
│   ├── logging.yaml
│   └── presets.yaml
├── docs/
│   ├── ai_usage_log.md
│   └── architecture.md
├── examples/
│   ├── example1_http.py
│   ├── example2_openai_sdk.py
│   └── example3_langchain.py
├── scripts/
│   ├── init_db.py
│   └── test_chat_engine.py
├── src/
│   ├── main.py
│   ├── core/
│   ├── interface/
│   ├── models/
│   ├── storage/
│   └── ui/tui/
└── tests/
```

## 快速开始

1. 克隆并进入仓库：

```powershell
git clone <your-repo-url> langchain-chat
Set-Location langchain-chat
```

2. 同步依赖：

```powershell
uv sync
```

3. 创建本地 `.env`：

```powershell
Copy-Item .env.example .env
```

4. 填写默认模型配置。至少需要将 `.env` 中这些占位值替换为真实 OpenAI 兼容服务配置：

```dotenv
API_BASE_URL=https://your-openai-compatible-endpoint/v1
API_KEY=your_api_key_here
MODEL_NAME=your_chat_model_name
```

5. 初始化当前配置的存储后端：

```powershell
uv run python scripts/init_db.py
```

6. 启动 TUI：

```powershell
uv run python -m src.main
```

也可以使用脚本入口：

```powershell
uv run python src/main.py
```

## 环境变量

`.env.example` 只保存变量名和占位值，不保存真实密钥。

| 变量 | 用途 | 何时需要 |
| --- | --- | --- |
| `API_BASE_URL` | 默认模型的 OpenAI 兼容 API 地址 | 使用默认模型时必填 |
| `API_KEY` | 默认模型 API Key | 使用默认模型时必填 |
| `MODEL_NAME` | 默认模型实际模型名 | 使用默认模型时必填 |
| `REASONING_API_BASE_URL` | `reasoning` 模型 API 地址 | 使用 `reasoning` 模型时必填 |
| `REASONING_API_KEY` | `reasoning` 模型 API Key | 使用 `reasoning` 模型时必填 |
| `REASONING_MODEL_NAME` | `reasoning` 实际模型名 | 使用 `reasoning` 模型时必填 |
| `MYSQL_HOST` | MySQL 主机 | 仅 MySQL 后端需要 |
| `MYSQL_PORT` | MySQL 端口 | 仅 MySQL 后端需要 |
| `MYSQL_USER` | MySQL 用户 | 仅 MySQL 后端需要 |
| `MYSQL_PASSWORD` | MySQL 密码 | 仅 MySQL 后端需要 |
| `MYSQL_DATABASE` | MySQL 数据库 | 仅 MySQL 后端需要 |

`.env.example` 中保留了 `APP_ENV` 注释作为 Step 15 计划提示。Step 14 尚未实现 `APP_ENV=dev|test|prod` 多环境加载，不要把它当作当前可用命令。

## config.yaml

主要配置项：

- `app.current_step`：当前教学步骤。
- `llm.default_model`：默认模型别名。
- `llm.available_models`：模型注册表，每个条目包含别名、显示名、默认模型名、环境变量名和 provider 描述。
- `llm.temperature`、`llm.max_tokens`、`llm.timeout`、`llm.max_retries`：默认生成参数。
- `storage.type`：可选 `sqlite`、`mysql`、`file`。
- `storage.sqlite.database_path`：SQLite 数据库文件路径，默认 `data/sqlite/app.db`。
- `storage.file.path`：FileBackend JSON 文件目录，默认 `data/filestore`。
- `storage.mysql.*_env`：MySQL 连接信息来自哪些环境变量。
- `conversation.title_max_length`：会话标题最大长度。
- `export.dir`：导出目录模板，当前为 `data/users/{username}/exports`。

## 存储后端选择

- SQLite：默认后端，适合本地教学、单机开发和轻量使用。
- File：使用五个 JSON 文件保存数据，适合观察数据结构和教学演示，不适合多进程并发写。
- MySQL：适合接近生产的集中式数据库场景，需要提前准备 MySQL 服务和数据库。

切换后端时修改 `config.yaml`：

```yaml
storage:
  type: sqlite  # sqlite | mysql | file
```

然后重新执行：

```powershell
uv run python scripts/init_db.py
```

## TUI 使用流程

1. 启动程序后进入主菜单。
2. 在“用户管理”中创建或切换当前用户。
3. 在“预设管理”中查看系统预设，或为当前用户创建自定义预设。
4. 进入“开始对话”，选择预设后开始多轮对话。
5. 在“会话管理”中查看、加载、重命名、删除或导出会话。
6. 在“搜索历史消息”中按当前用户范围搜索消息。
7. 在“设置”中设置当前用户默认模型。
8. 对话过程中可使用 TUI 已实现的模型切换流程继续同一会话。

## 数据、导出和日志位置

- SQLite 数据库：`data/sqlite/app.db`
- FileBackend 数据：`data/filestore/`
- Markdown 导出：`data/users/{username}/exports/`
- 文件日志：`logs/app.log`
- 日志格式：文件日志为 JSONL，每行是一个独立 JSON 对象。

这些路径属于运行时数据，默认不应提交到 Git。

## 测试和代码检查

运行默认测试：

```powershell
uv run pytest -q
```

生成覆盖率报告：

```powershell
uv run pytest --cov=src --cov-report=term-missing
```

Ruff lint：

```powershell
uv run ruff check .
```

Ruff 格式检查：

```powershell
uv run ruff format --check .
```

编译检查：

```powershell
uv run python -m compileall src
```

## MySQL 集成测试

默认测试不会连接 MySQL。显式运行 MySQL 集成测试前，需要准备测试数据库，并确保数据库名包含 `test`，避免误用正式库。

PowerShell 示例：

```powershell
$env:RUN_MYSQL_TESTS = "1"
$env:MYSQL_TEST_DATABASE = "langchain_chat_test"
$env:MYSQL_HOST = "localhost"
$env:MYSQL_PORT = "3306"
$env:MYSQL_USER = "myuser"
$env:MYSQL_PASSWORD = "your_mysql_password_here"
uv run pytest tests/test_mysql_backend.py -q
```

未设置 `RUN_MYSQL_TESTS=1` 时，MySQL 集成测试会被 pytest 标记为 skipped。

## 常见问题

- 模型配置缺失：检查 `.env` 中 `API_BASE_URL`、`API_KEY`、`MODEL_NAME` 是否仍是占位值。
- API 请求失败：确认 API 地址支持 OpenAI 兼容接口，模型名和 Key 正确，网络可访问。
- SQLite 数据位置：默认在 `data/sqlite/app.db`，可在 `config.yaml` 修改。
- File 数据位置：默认在 `data/filestore/`，删除该目录会删除 FileBackend 数据。
- MySQL 连接失败：检查 `storage.type=mysql`、MySQL 服务状态、数据库名、用户权限和 `.env`。
- 日志位置：查看 `logs/app.log`，文件日志为 JSONL。
- pytest 中 MySQL 被跳过：这是默认行为；设置 `RUN_MYSQL_TESTS=1` 后才会运行。

## 安全说明

- 不提交真实 `.env`。
- 不在 README、测试或日志中写入真实 API Key、Authorization 或数据库密码。
- 运行时数据、导出文件和日志不应提交。
- 文件日志默认不记录完整用户 Prompt、模型回复或 system prompt。

## 当前限制

- 当前只有 TUI，没有 WebUI。
- 多模型并行对比、图文上传、语音输入输出和 Tool Calling 仅在接口层预留，尚未实现。
- Step 15 的多环境覆盖配置尚未实现。
- FileBackend 不提供多进程并发写事务保证。
- 默认测试不验证真实 LLM 服务和真实 MySQL 服务。

## 后续扩展方向

- Step 15：实现基础配置 + 环境覆盖配置，计划支持 dev/test/prod 配置分层。
- WebUI：通过实现基础 UI 协议接入 core，不让 core 依赖 Web 框架。
- 多模型并行对比：基于 Step 14 预留的数据契约展示多个模型结果。
- 图文和文件输入：通过附件元数据接口传递文件引用。
- 语音：预留 STT/TTS 请求和结果边界。
- Tool Calling：预留工具调用确认、进度和结果展示边界。

## Git Step / Tag

主要里程碑：

- `step-11-mysql`：MySQL 异步存储后端。
- `step-12-logging-file`：FileBackend 和结构化日志。
- `step-13-tests`：核心模块单元测试。
- `step-14-docs-extend`：README、架构文档和扩展接口预留。

本步骤不会自动创建 commit、tag 或 push。
