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

## Step 4：用户管理模块与 TUI 用户菜单

- 日期：2026-07-13
- 使用工具：Codex
- 三层数据流：TUIApp 获取输入和显示结果，UserManager 处理用户业务规则，StorageBackend/SQLiteBackend 负责持久化到 SQLite。
- UserManager 依赖注入：`UserManager` 构造函数接收 `StorageBackend`，不导入或创建 SQLiteBackend，不写 SQL。
- 当前用户状态：`current_user` 和 `current_session` 维护在 TUIApp 实例内；切换用户时清空 `current_session`，重启后允许回到未登录状态。
- 二次确认：删除用户的二次确认放在 UI 层，只有输入 `yes` 才调用业务层删除；禁止删除当前登录用户。
- try/finally：`main.py` 启动时创建并初始化存储后端，TUI 退出、Ctrl+C 或异常时都在 `finally` 中关闭后端连接。
- 实际验证命令：`uv run python scripts/init_db.py`、`uv run python -c "import sys; sys.path.insert(0,'src'); from core.user_manager import UserManager; print('UserManager OK:',UserManager.__name__)"`、`uv run python -c "import sys; sys.path.insert(0,'src'); from ui.tui.app import TUIApp; print('TUIApp OK:',TUIApp.__name__)"`、`uv run python -m compileall src`、`uv run python src/main.py`、`uv run ruff check src scripts tests`、`git diff --check`、`git status --short`、`git diff --stat`。
- 实际结果：Step 3 初始化脚本通过；`UserManager` 和 `TUIApp` 均可导入；`compileall` 通过；应用可启动，横幅显示 Step 4，主菜单显示“当前用户：未登录”，通过输入 `7` 可退出；Ruff 检查通过。TUI 用户管理的完整交互流程留给用户手工验证。
- 人工待验证流程：创建 `alice`；重复创建 `alice`；创建 `bob`；列出用户；切换 `bob`；删除当前 `bob` 被拒绝；删除 `alice` 并进行二次确认；重启后 `bob` 仍存在。
- 未完成项目：本步骤不实现预设管理、会话管理、对话引擎或大模型调用。
- 建议 commit：`feat: step 4 - 用户管理业务层、TUI 用户菜单与存储后端接入`
- 建议 tag：`step-4-user-mgmt`

## Step 5：预设管理模块与 TUI 预设菜单

- 日期：2026-07-13
- 使用工具：Codex
- 内置与自定义预设设计：系统内置预设来自 `config/presets.yaml`，`user_id=None`、`is_builtin=True`、所有用户共享且只读；用户自定义预设归属当前用户，`is_builtin=False`，可创建、编辑、删除。
- 幂等导入：启动时通过 PresetManager 读取 YAML，基于内置预设名称去重；第一次导入 YAML 数量，第二次导入 0。
- save_preset bug 原因：旧风险是只判断 `id is None`，而项目新建模型使用 `id=0`；修复为 `not preset.id` 作为新增，并要求更新不存在 ID 时明确失败。
- get_preset_by_id 最终修复：在 StorageBackend 增加 `get_preset_by_id` 抽象方法，SQLiteBackend 用参数化 SQL 实现，PresetManager 查询单个预设只使用该方法。
- read_text 默认值：`read_text(prompt_text, default="")` 支持显示当前值；输入为空时返回默认值，保持 Step 4 默认行为兼容。
- 权限和用户隔离：未登录不能操作预设管理；内置预设不能编辑或删除；用户只能查看自己的自定义预设和内置预设，不能跨用户修改或删除。
- 自动验证结果：`PresetManager` 可导入；`SQLiteBackend.__abstractmethods__` 为 `frozenset()`；`compileall` 通过；应用可启动并退出，横幅显示 Step 5；真实 `app.db` 中内置预设数量为 5，重复启动未再次导入；临时数据库验证中第一次导入内置预设 5 个、第二次导入 0 个，`Preset(id=0)` 保存后 ID 大于 0，`get_preset_by_id` 可查询，自定义预设可更新和删除，alice/bob 私人预设互不可见；Ruff 和 Pytest 均通过；`git diff --check` 退出状态为 0，仅有 Windows 换行提示。
- 用户待手工验证内容：查看内置预设；未登录时预设管理提示先创建或切换用户；创建自定义预设；编辑自定义预设并验证回车保留；尝试编辑/删除内置预设被拒绝；删除自定义预设需二次确认；重复启动后内置预设不重复导入。
- 未完成项目：本步骤不实现聊天时选择预设，不调用 LLM，不实现 Step 6。
- 建议 commit：`feat: step 5 - 预设管理业务层、TUI 预设菜单与内置预设导入`
- 建议 tag：`step-5-presets`

## Step 5 补充：编号系统修复

- 日期：2026-07-13
- 使用工具：Codex
- 问题现象：预设列表中用户看到的编号直接显示为数据库主键，例如内置预设从 8 开始，容易误解为菜单、用户、预设共用同一个编号系统。
- 根本原因：SQLite 五张业务表主键本身独立，存储层没有全局 ID 生成器；问题发生在 TUI 展示层，预设列表和可编辑/可删除列表直接把 `preset.id` 当成用户选择编号展示和输入。
- 数据库 ID 与展示序号区别：数据库 ID 是持久化主键，允许因历史插入/删除产生空缺且不重排；展示序号是当前列表局部编号，每次显示独立从 1 开始。
- 修改文件：`src/ui/tui/app.py`、`docs/ai_usage_log.md`。
- 是否涉及数据库结构：不涉及；`users`、`sessions`、`messages`、`presets`、`user_configs` 均保持独立 `id INTEGER PRIMARY KEY AUTOINCREMENT`。
- 临时数据库验证结果：使用 `data/sqlite/_id_test.db` 创建空库，五张表第一条 ID 均为 1，第二条 ID 均为 2；多个用户不会推动 `preset.id`，多个预设不会推动 `user.id`；验证后已删除临时数据库。
- TUI 编号修复结果：用户列表、预设列表、自定义预设编辑/删除列表使用“序号”作为用户可见编号；编辑/删除时输入列表序号，并通过局部映射转换到真实数据库 ID。
- 回归验证结果：`uv run python -m compileall src scripts`、`uv run python scripts/init_db.py`、`uv run python src/main.py`、`uv run ruff check src scripts tests`、`uv run pytest` 均通过；`git diff --check` 待最终检查。
- 用户需要手工验证的内容：在 TUI 中创建或切换用户后进入预设管理，确认预设列表序号从 1 开始；确认自定义预设编辑/删除输入的是列表序号，且数据库 ID 不连续时仍能定位正确对象。

## Step 5 补充：隐藏数据库主键展示

- 日期：2026-07-13
- 使用工具：Codex
- 数据库主键与展示序号的区别：数据库主键是内部持久化标识，用于外键、查询、权限校验和更新删除；展示序号是当前 TUI 列表局部生成的临时编号，每个列表都从 1 开始。
- 为什么隐藏数据库 ID：普通用户只需要识别“第几个预设”和预设名称，数据库 ID 是实现细节；隐藏后可以减少对“编号共用”的误解，也避免把不连续主键误认为异常。
- presets 单表设计保持不变：系统内置预设与用户自定义预设继续共同存放在 `presets` 表；内置预设使用 `user_id=None`、`is_builtin=True`，自定义预设使用当前用户 ID、`is_builtin=False`。
- 修改文件：`src/ui/tui/app.py`、`docs/ai_usage_log.md`。
- 验证结果：`uv run python -m compileall src` 通过；`uv run python src/main.py` 可启动并通过输入 `7` 退出；使用已有用户 `bob` 只读进入预设列表，确认表头不再包含“数据库 ID”列，当前用户状态只显示用户名；`git diff --check` 待最终检查。
- 用户待手工验证项目：预设列表没有“数据库 ID”列；预设序号从 1 开始；编辑/删除输入展示序号且能定位正确对象；当前用户状态只显示用户名；内置预设仍不可编辑和删除；不同用户的私人预设仍隔离；重复启动后内置预设不重复。
