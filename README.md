# langchain-chat

`langchain-chat` 是一个基于 LangChain 的多用户、多会话 TUI Chatbot，也是按 Step 演进的工程化教学项目。

当前进度：`Step 15 多环境配置区分`。

## 主要功能

- 多轮对话：按用户和会话保存历史，并在继续对话时加载上下文。
- 流式输出：ChatEngine 使用 LangChain / OpenAI 兼容接口异步流式返回分块。
- 多用户隔离：用户、会话、消息、自定义预设和用户配置按 `user_id` 隔离。
- 会话管理：支持创建、加载、重命名、删除、搜索和 Markdown 导出。
- Prompt 预设：支持系统内置预设和用户自定义预设。
- 模型切换：支持用户默认模型和会话运行时模型切换。
- 可插拔存储：支持 SQLite、MySQL 和 JSON File 三种后端。
- 结构化日志：控制台日志面向开发者，文件日志为 JSONL。
- 自动化测试：核心模块使用 pytest，默认不依赖真实 LLM、互联网或 MySQL Server。
- 多环境配置：通过 `APP_ENV=dev|test|prod` 切换 YAML、密钥文件和数据源。

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

- Python 3.10 到 3.12。
- uv，用于同步依赖、运行命令和维护锁文件。
- MySQL 仅在 `APP_ENV=prod`、手动选择 `storage.type=mysql` 或显式运行 MySQL 集成测试时需要。

## 目录结构

```text
langchain-chat/
|-- .env.example
|-- config.yaml
|-- config.dev.yaml
|-- config.test.yaml
|-- config.prod.yaml
|-- pyproject.toml
|-- uv.lock
|-- README.md
|-- config/
|   |-- logging.yaml
|   `-- presets.yaml
|-- docs/
|   |-- ai_usage_log.md
|   `-- architecture.md
|-- examples/
|-- scripts/
|   `-- init_db.py
|-- src/
|   |-- main.py
|   |-- core/
|   |-- interface/
|   |-- models/
|   |-- storage/
|   `-- ui/tui/
`-- tests/
```

## 快速开始

```powershell
git clone <your-repo-url> langchain-chat
Set-Location langchain-chat
uv sync
```

选择环境，默认未设置时为 `dev`：

```powershell
$env:APP_ENV = "dev"
```

创建当前环境的本地密钥文件。Step 15 后程序只加载当前环境对应的 `.env.{env}`，不会回退读取旧 `.env`：

```powershell
Copy-Item .env.example .env.dev
```

编辑 `.env.dev`，至少填入开发环境模型变量：

```dotenv
DEV_API_BASE_URL=https://your-openai-compatible-endpoint/v1
DEV_API_KEY=your_dev_api_key_here
DEV_MODEL_NAME=your_chat_model_name
```

初始化当前环境配置的存储后端：

```powershell
uv run python scripts/init_db.py
```

启动 TUI：

```powershell
uv run python -m src.main
```

也可以使用脚本入口：

```powershell
uv run python src/main.py
```

清理 PowerShell 中的环境选择：

```powershell
Remove-Item Env:APP_ENV -ErrorAction SilentlyContinue
```

## 多环境配置

配置加载顺序固定为：

1. 读取进程环境变量 `APP_ENV`，未设置时默认为 `dev`。
2. 只允许 `dev`、`test`、`prod`，会去除首尾空格并转为小写。
3. 读取 `config.yaml`。
4. 读取 `config.{APP_ENV}.yaml`。
5. 对两个 YAML 做递归深度合并：dict 递归合并，scalar 覆盖，list 整体替换。
6. 只加载 `.env.{APP_ENV}`，并使用 `override=False` 保留操作系统环境变量的更高优先级。
7. 构造 `AppConfig`，业务层只读取最终配置对象。

非法环境会立即报错，不会静默回退到 dev。

### 切换命令

PowerShell：

```powershell
$env:APP_ENV = "dev"
$env:APP_ENV = "test"
$env:APP_ENV = "prod"
```

POSIX shell：

```bash
export APP_ENV=dev
export APP_ENV=test
export APP_ENV=prod
```

### 三环境差异

| 环境 | YAML | dotenv | 默认存储 | 数据路径 | 说明 |
| --- | --- | --- | --- | --- | --- |
| dev | `config.dev.yaml` | `.env.dev` | SQLite | `data/dev/sqlite/app.db` | 本地开发和手工调试。 |
| test | `config.test.yaml` | `.env.test` | SQLite | `data/test/sqlite/app.db` | 自动测试环境；测试仍优先使用 `tmp_path`。 |
| prod | `config.prod.yaml` | `.env.prod` | MySQL | MySQL 数据库 | 需要显式提供生产模型和 MySQL 变量，禁止回退到 dev。 |

## `.env.example` 变量

`.env.example` 只保存变量名和占位值。复制为 `.env.dev`、`.env.test` 或 `.env.prod` 后再填写真实值。

| 变量 | 用途 | 需要环境 |
| --- | --- | --- |
| `DEV_API_BASE_URL` / `DEV_API_KEY` / `DEV_MODEL_NAME` | 开发默认模型 | dev |
| `DEV_REASONING_API_BASE_URL` / `DEV_REASONING_API_KEY` / `DEV_REASONING_MODEL_NAME` | 开发推理模型 | dev，使用 reasoning 时 |
| `TEST_API_BASE_URL` / `TEST_API_KEY` / `TEST_MODEL_NAME` | 测试默认模型占位 | test；自动测试不会真实调用 |
| `TEST_REASONING_*` | 测试推理模型占位 | test，使用 reasoning 时 |
| `PROD_API_BASE_URL` / `PROD_API_KEY` / `PROD_MODEL_NAME` | 生产默认模型 | prod，必填 |
| `PROD_REASONING_*` | 生产推理模型 | prod，使用 reasoning 时 |
| `PROD_MYSQL_HOST` / `PROD_MYSQL_PORT` / `PROD_MYSQL_USER` / `PROD_MYSQL_PASSWORD` / `PROD_MYSQL_DATABASE` | 生产 MySQL 连接 | prod，必填 |

从旧 `.env` 迁移时，将原有模型变量复制到 `.env.dev` 并改名为 `DEV_*`；生产变量放入 `.env.prod`，不要混用。

## config.yaml

`config.yaml` 是共享基础配置，不写真实密钥。主要字段：

- `app.current_step`：当前教学步骤。
- `llm.default_model`：默认模型别名。
- `llm.available_models`：模型注册表；环境覆盖文件会替换该列表以使用环境专属变量名。
- `llm.temperature`、`llm.max_tokens`、`llm.timeout`、`llm.max_retries`：默认生成参数。
- `storage.type`：`sqlite`、`mysql` 或 `file`。
- `storage.sqlite.database_path`：SQLite 数据库文件路径。
- `storage.file.path`：FileBackend JSON 文件目录。
- `storage.mysql.*_env`：MySQL 连接信息来自哪些环境变量。
- `conversation.title_max_length`：会话标题最大长度。
- `export.dir`：Markdown 导出目录模板。

## 存储后端选择

- SQLite：适合本地开发、教学和轻量使用。dev/test 默认使用 SQLite，但数据文件互相隔离。
- File：使用五个 JSON 文件保存实体，适合观察数据结构和教学演示，不适合多进程并发写。
- MySQL：适合接近生产的集中式数据库场景。prod 默认使用 MySQL，缺少必要变量会失败，不会回退 SQLite。

修改后端后执行：

```powershell
uv run python scripts/init_db.py
```

## TUI 使用流程

1. 启动程序进入主菜单。
2. 在用户管理中创建或切换当前用户。
3. 在预设管理中查看系统预设，或创建当前用户的自定义预设。
4. 开始对话，选择预设并发送消息。
5. 在会话管理中加载、重命名、删除或导出会话。
6. 搜索历史消息时只返回当前用户范围内的结果。
7. 在设置中更新当前用户默认模型，或在会话流程中切换模型。

## 数据、导出和日志位置

- dev SQLite：`data/dev/sqlite/app.db`
- test SQLite：`data/test/sqlite/app.db`
- prod MySQL：由 `.env.prod` 的 `PROD_MYSQL_*` 指定
- FileBackend：`storage.file.path` 指定，dev/test 分别为 `data/dev/filestore`、`data/test/filestore`
- Markdown 导出：`export.dir` 指定，dev/test/prod 分别进入对应环境的 `data/{env}/users/{username}/exports`
- 文件日志：`logs/app.log`，JSONL，每一行是独立 JSON 对象

这些路径属于运行时数据，默认不应提交到 Git。

## 测试和代码检查

默认测试：

```powershell
$env:APP_ENV = "test"
uv run pytest -q
```

覆盖率：

```powershell
uv run pytest --cov=src --cov-report=term-missing
```

Ruff：

```powershell
uv run ruff check .
uv run ruff format --check .
```

编译检查：

```powershell
uv run python -m compileall src tests
```

## MySQL 集成测试

默认测试不会连接 MySQL。显式运行 MySQL 集成测试前，准备测试数据库，并确保数据库名包含 `test`：

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

- 模型配置缺失：确认当前 `APP_ENV`，再检查对应 `.env.{env}` 中的 `DEV_*`、`TEST_*` 或 `PROD_*` 变量是否仍是占位值。
- API 请求失败：确认 API 地址支持 OpenAI 兼容接口，模型名和 Key 正确，网络可访问。
- SQLite 数据位置：dev 为 `data/dev/sqlite/app.db`，test 为 `data/test/sqlite/app.db`。
- File 数据位置：查看当前环境的 `storage.file.path`。
- MySQL 连接失败：prod 需要 `PROD_MYSQL_*`，MySQL 服务、数据库、用户权限都必须可用。
- 日志位置：查看 `logs/app.log`，文件日志为 JSONL。
- pytest 中 MySQL 被跳过：这是默认行为；设置 `RUN_MYSQL_TESTS=1` 后才会运行。
- APP_ENV 拼写错误：程序会报配置错误，不会自动回退。

## 安全说明

- 不提交 `.env`、`.env.dev`、`.env.test`、`.env.prod` 或其他 `.env.*` 文件。
- `.env.example` 只包含占位值，不包含真实 API Key、Authorization、数据库密码或内部地址。
- 日志不记录真实密钥、数据库密码、完整连接串、完整用户 Prompt、模型回复或 system prompt。
- 运行时数据、导出文件和日志不应提交。
- prod 不会回退到 dev 的密钥、模型或数据库。

## 当前限制

- 当前只有 TUI，没有 WebUI。
- 多模型并行对比、图文上传、语音输入输出和 Tool Calling 仅在接口层预留，尚未实现业务功能。
- FileBackend 不提供多进程并发写事务保证。
- 默认测试不验证真实 LLM 服务，也不验证真实 MySQL 服务。
- prod 真实冒烟需要用户提供 MySQL 与模型环境后手工执行。

## 后续扩展方向

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
- `step-15-envs`：dev/test/prod 多环境配置隔离。该标签应在三环境验收都完成后创建。

本步骤不会自动创建 commit、tag 或 push。
