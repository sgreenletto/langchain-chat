# AI 辅助开发记录

## Step 1：项目初始化与工程化配置

- 日期：2026-07-13
- 使用工具：Codex
- 本步骤目标：完成项目初始化和工程化配置，建立可以运行、可追踪、可继续扩展的 Python 项目骨架。
- 用户提供的主要约束：只在 `D:\project\langchain-chat` 工作；不复制项目；不创建真实 `.env`；不提前实现 TUI、数据库、用户管理、会话管理、LangChain 调用或多环境加载；本轮不执行 commit 和 tag。
- Codex 检查的项目文档：仓库内 `docs/需求说明文档.md`、`docs/实施步骤计划.md`、`docs/需求变更与扩展登记.md`、`docs/Git命令与操作教学.md`、`docs/uv包管理器教学文档.md`、`docs/Step1-项目初始化教学文档.md` 均不存在，因此未读取到老师原始文档。
- 新建或修改的文件：`.gitignore`、`.env.example`、`pyproject.toml`、`config.yaml`、`config/logging.yaml`、`config/presets.yaml`、`src/__init__.py`、`src/main.py`、`README.md`、`docs/ai_usage_log.md`；`uv.lock` 由 `uv sync --python 3.12.13` 生成。
- 关键设计决策：Step 1 保持运行依赖为空；使用 Python 3.12.13；敏感信息只放入本地 `.env`，业务配置放入 `config.yaml`，日志配置放入 `config/logging.yaml`，系统预设放入 `config/presets.yaml`。
- 没有采用的方案及原因：未创建真实 `.env`，避免泄露敏感信息；未创建 `config.dev.yaml`、`config.test.yaml`、`config.prod.yaml`，因为 Step 15 才启用多环境配置；未引入 LangChain、Rich、prompt_toolkit、Pydantic 或数据库依赖，因为 Step 1 只建立地基。
- 实际运行的验证命令：`uv sync --python 3.12.13`、`uv run python --version`、`uv run python src/main.py`、`uv run python -m src.main`、`uv run python -m compileall src`、`git diff --check`、`git status --short`、`git diff --stat`、`git check-ignore .env`、`git check-ignore .venv`。
- 验证结果：`uv sync --python 3.12.13` 成功，使用 CPython 3.12.13 并创建 `.venv`；`uv run python --version` 输出 `Python 3.12.13`；脚本入口和模块入口均成功打印 Step 1 启动横幅；`compileall` 成功；`git diff --check` 成功且无输出；`.env` 与 `.venv` 均被 Git 忽略。
- 用户仍需人工检查的内容：确认仓库内老师原始文档是否需要后续补充；确认 Step 1 文件内容是否符合课程要求。
- 当前已知风险：仓库内缺少用户要求检查的 6 份原始教学文档，本次只能依据用户本轮提供的 Step 1 要求实现。
- 计划使用的 commit：`chore: step 1 - 项目初始化与工程化配置`
- 计划使用的 tag：`step-1-init`

## Step 2：数据模型与 TUI 骨架

- 日期：2026-07-13
- 使用工具：Codex
- 任务目标：使用 Pydantic v2 定义数据模型，使用 ABC 定义异步存储后端接口，实现 `.env` + `config.yaml` 配置加载，并建立可交互的 TUI 主菜单骨架。
- 读取的教学文档：仓库内 `docs/需求说明文档.md`、`docs/实施步骤计划.md`、`docs/Step2-数据模型与TUI骨架教学文档.md` 均不存在，因此未能读取老师原始 Step 2 文档。
- 用户提出的约束：只在 `D:\project\langchain-chat` 工作；必须保留 `main` 分支和 remote；依赖只能添加 Pydantic、pydantic-settings、python-dotenv、PyYAML、Rich、prompt_toolkit；不得实现 SQLiteBackend、数据库、用户管理、预设管理、LangChain 或真实 API 调用；不得提交 `.env`；不得执行 `git push`。
- 新增和修改文件：新增 `src/core/config_manager.py`、`src/models/schemas.py`、`src/storage/base.py`、`src/interface/ui_protocol.py`、`src/ui/tui/app.py`、`src/ui/tui/menu_view.py`、`src/ui/tui/chat_view.py`、`src/ui/tui/widgets.py` 及各层 `__init__.py`；修改 `src/main.py`、`config.yaml`、`README.md`、`pyproject.toml`、`uv.lock`、`docs/ai_usage_log.md`。
- 关键设计决策：源码内部采用相对于 `src` 的导入方式；`src/main.py` 注入 `src` 路径保证 `uv run python src/main.py` 稳定运行；模型只负责结构和校验；存储层只定义抽象契约；TUI 菜单只提供可进入的桩函数。
- 实际执行命令：`uv add pydantic pydantic-settings python-dotenv pyyaml rich prompt_toolkit`、`uv sync`、`uv run python -c "import pydantic,pydantic_settings,dotenv,yaml,rich,prompt_toolkit; print('全部导入成功')"`、`uv run python -c "import sys; sys.path.insert(0,'src'); from models.schemas import User,Session,Message,Preset,UserConfig; u=User(id=1,username='test'); m=Message(id=1,session_id=1,role='human',content='hello'); print('User OK:',u.username); print('Message OK:',m.role)"`、`uv run python -c "import sys; sys.path.insert(0,'src'); from storage.base import StorageBackend; print('StorageBackend OK:',StorageBackend.__name__)"`、`uv run python -c "import sys; sys.path.insert(0,'src'); from core.config_manager import get_config; c=get_config(); print('Config OK')"`、`uv run python -c "import sys; sys.path.insert(0,'src'); from ui.tui.app import TUIApp; print('TUIApp OK:',TUIApp.__name__)"`、`uv run python -m compileall src`、`git diff --check`、`git status --short`、`git diff --stat`、`uv run python src/main.py`。
- 实际结果：依赖安装和 `uv sync` 成功；依赖导入成功；Pydantic 模型实例化成功；`StorageBackend` 导入成功；`get_config()` 读取并校验配置成功；`TUIApp` 导入成功；`compileall` 成功；`git diff --check` 退出状态为 0，仅出现 Windows 换行提示；通过向 `uv run python src/main.py` 输入 `7` 验证 TUI 主菜单可启动并退出。未对所有菜单做人工交互验证。
- 需要用户手工验证的内容：启动 `uv run python src/main.py` 后，人工操作各 TUI 菜单是否符合课堂预期。
- 当前风险：仓库内缺少 Step 2 指定教学文档，本次实现依据用户本轮明确要求完成。
- 建议 commit：`feat: step 2 - 数据模型、存储接口、配置管理与 TUI 骨架`
- 建议 tag：`step-2-skeleton`

## Step 3：SQLite 存储后端与数据库初始化

- 日期：2026-07-13
- 使用工具：Codex
- 目标：实现 SQLiteBackend、StorageFactory、`scripts/init_db.py`，创建五张业务表，并完成异步存储层冒烟测试。
- aiosqlite：通过 `uv add aiosqlite` 安装，用于正式 SQLite 后端；未使用同步 `sqlite3` 或 SQLAlchemy。
- StorageFactory：`sqlite` 返回 `SQLiteBackend`，`mysql` 提示 Step 11 实现，`file` 提示 Step 12 实现，未知类型抛出 `ValueError`。
- 五张表：`users`、`sessions`、`messages`、`presets`、`user_configs`。
- 外键和级联：用户删除级联会话、消息、自定义预设和用户配置；会话删除级联消息；预设删除时会话引用置空。
- 所有实现方法：SQLiteBackend 覆盖当前 `StorageBackend` 的 21 个抽象方法，并额外提供 `list_table_names()` 供初始化脚本验证。
- init_db 冒烟过程：创建并查询用户，创建预设和会话，保存 human/ai 消息，读取消息列表和搜索结果，保存并读取用户配置，删除用户并验证关联数据级联删除。
- 两次运行结果：两次执行 `uv run python scripts/init_db.py` 均成功；实际数据库路径为 `D:\project\langchain-chat\data\sqlite\app.db`；五张业务表为 `messages`、`presets`、`sessions`、`user_configs`、`users`；两次均完成用户、预设、会话、消息、用户配置的冒烟流程，并验证删除用户后关联会话、消息、预设和配置已级联清理。
- 额外验证：`SQLiteBackend.__abstractmethods__` 为 `frozenset()`；`uv run ruff check src scripts tests` 通过；`uv run pytest` 通过，2 个测试全部通过；`uv run python src/main.py` 可启动 Step 2 TUI 并通过输入 `7` 退出。
- 未完成项目：本步骤不接入 TUI，不实现 UserManager、PresetManager、SessionManager、ChatEngine、MySQLBackend 或 FileBackend。
- 建议 commit：`feat: step 3 - SQLite 存储后端、工厂模式与数据库初始化`
- 建议 tag：`step-3-sqlite`
