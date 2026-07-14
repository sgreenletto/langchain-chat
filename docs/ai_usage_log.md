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

## Step 6：对话引擎

- 日期：2026-07-13
- 使用工具：Codex
- 本次任务摘要：实现无状态 `ChatEngine`，支持 OpenAI 兼容 API、完整 LangChain 消息历史、非流式调用、异步流式输出、Token 用量提取、超时和自动重试；本步骤不接入完整 TUI 对话循环。
- Codex 执行内容：检查 Step 5 标签和干净工作区；通过 `uv add` 添加 `langchain`、`langchain-openai`、`openai`、`httpx`；检查本地 `ChatOpenAI` 构造签名；补齐配置管理出口；实现 ChatEngine、三层调用示例和冒烟脚本；补充无外部依赖的单元测试。
- 修改文件：`pyproject.toml`、`uv.lock`、`config.yaml`、`README.md`、`docs/ai_usage_log.md`、`src/core/config_manager.py`、`src/core/chat_engine.py`、`src/ui/tui/widgets.py`、`src/ui/tui/app.py`、`examples/__init__.py`、`examples/example1_http.py`、`examples/example2_openai_sdk.py`、`examples/example3_langchain.py`、`scripts/test_chat_engine.py`、`tests/test_chat_engine.py`。
- 关键设计决策：`ChatEngine` 不保存用户、会话或消息历史；调用方每次传入完整 `BaseMessage` 列表；流式接口通过最终 `ChatStreamEvent(is_final=True)` 暴露 Token 用量；未返回 usage 时标记为“服务未提供”，不伪造 Token。
- 验证命令及结果：`uv sync` 成功；`uv run ruff check .` 通过；`uv run pytest` 通过，7 个测试全部通过；`uv run python -c "from src.core.chat_engine import ChatEngine; print(ChatEngine.__name__)"` 输出 `ChatEngine`；`uv run python -m examples.example1_http`、`example2_openai_sdk`、`example3_langchain` 均调用成功且未输出密钥；`uv run python scripts/test_chat_engine.py` 完成非流式、历史、SystemMessage、流式和异常处理冒烟测试，并获得服务返回的 Token usage。
- 未完成项目：未实现 Step 7 的完整 TUI 对话循环；未修改数据库结构；未新增会话管理或对话持久化逻辑。
- commit 信息：`feat: step 6 - 对话引擎（LLM 调用、流式输出、Token 统计）与 LLM 编程示例`

## Step 7：会话管理与 TUI 多轮流式对话

- 日期：2026-07-13
- 使用工具：Codex
- 本次任务摘要：实现 `SessionManager` 会话业务层，并将 Step 6 的无状态 `ChatEngine` 接入 TUI 对话视图，支持登录保护、新建/继续会话、预设选择、多轮上下文、流式回复、Token 累计、消息持久化和基础斜杠命令。
- Codex 执行内容：检查 Step 6 标签和干净工作区；新增 `src/core/session_manager.py`；替换 `src/ui/tui/chat_view.py` 桩函数；改造 `TUIApp` 和 `main.py` 为依赖注入；补充 prompt_toolkit 对话输入历史；更新当前步骤配置、README 和测试。
- 修改文件：`config.yaml`、`README.md`、`docs/ai_usage_log.md`、`src/core/session_manager.py`、`src/main.py`、`src/storage/base.py`、`src/storage/factory.py`、`src/storage/__init__.py`、`src/ui/tui/app.py`、`src/ui/tui/chat_view.py`、`src/ui/tui/widgets.py`、`tests/test_session_manager.py`。
- 关键设计决策：`ChatEngine` 继续无状态；`SessionManager` 通过 `StorageBackend` 抽象操作会话和消息；TUI 只负责交互展示；所有列表选择使用从 1 开始的临时序号，不显示或要求用户输入数据库 ID。
- 验证命令及结果：`uv sync` 通过；`uv run ruff check .` 通过；`uv run pytest` 通过，8 个测试全部通过；`uv run python -c "from src.core.session_manager import SessionManager; print(SessionManager.__name__)"` 输出 `SessionManager`；`uv run python -m compileall src scripts tests` 通过；`uv run python -m src.main` 可启动并退出，横幅显示 Step 7；自动输入“开始对话”验证未登录保护通过。
- 用户待手工验证项目：预设选择、无预设会话、流式回复、多轮记忆、Token 展示、`/help`、`/rename`、`/new`、`/exit`、上箭头输入历史、重启后加载历史继续、用户 A 与用户 B 数据隔离。
- commit 信息：`feat: step 7 - 会话管理与 TUI 多轮流式对话`

## Step 8：会话管理完善与分层重构

- 日期：2026-07-13
- 使用工具：Codex
- 本次任务摘要：完善当前用户会话列表、加载、重命名和删除功能，删除前二次确认，删除当前会话后清空 TUI 状态，并修复 UI 直接访问存储后端的分层穿透风险。
- Codex 执行内容：检查 Step 7 标签和干净工作区；扩展 `SessionManager` 的 `list_sessions`、`get_session`、`rename_session`、`delete_session`；在 TUIApp 中实现会话管理子菜单；更新 chat_view 调用新业务接口；更新 Step 8 配置、README 和测试。
- 修改文件：`config.yaml`、`README.md`、`docs/ai_usage_log.md`、`src/core/session_manager.py`、`src/storage/sqlite_backend.py`、`src/ui/tui/app.py`、`src/ui/tui/chat_view.py`、`src/ui/tui/menu_view.py`、`tests/test_session_manager.py`。
- 关键设计决策：会话归属校验放在 SessionManager；UI 只使用临时显示序号映射到 Session 对象；删除会话依赖存储层 `delete_session` 和数据库级联清理消息；不修改数据库 schema。
- 验证命令及结果：`uv sync` 通过；`uv run ruff check .` 通过；`uv run pytest` 通过，8 个测试全部通过；`Get-ChildItem src\ui -Recurse -Filter *.py | Select-String "\.backend\."` 无输出；`uv run python -m compileall src tests` 通过；`uv run python -m src.main` 可启动并退出，横幅显示 Step 8；自动输入“会话管理”验证未登录保护通过。
- 用户待手工验证项目：空会话列表、多个会话排序、加载历史继续对话、重命名、空标题拒绝、删除取消、删除确认、删除后消息不可加载、删除当前会话后状态清空、用户隔离、列表序号从 1 开始。
- commit 信息：`feat: step 8 - 完善会话列表、加载、重命名与删除`

## Step 9：对话搜索、查看会话记录与模型配置源修复

- 日期：2026-07-13
- 使用工具：Codex
- 本次任务摘要：修复用户和会话记录模型名来源不一致问题；在会话管理中增加完整会话记录查看；在主菜单中增加当前用户范围内的历史消息关键词搜索。
- Codex 执行内容：检查 Step 8 标签和干净工作区；确认 ChatEngine 实际使用 `config.model_name`；将用户默认模型和新建会话模型统一为 `config.model_name`；扩展 SessionManager 搜索和会话消息读取接口；在 TUIApp 中实现记录查看和搜索结果按会话分组显示。
- 修改文件：`config.yaml`、`README.md`、`docs/ai_usage_log.md`、`src/core/session_manager.py`、`src/ui/tui/app.py`、`tests/test_session_manager.py`。
- 关键设计决策：旧数据库中的历史模型名不自动迁移；搜索空关键词直接返回空结果；UI 不访问 backend；搜索结果先构造当前用户 session map，再按会话分组，避免每条消息重复查询会话。
- 验证命令及结果：`uv sync` 通过；`uv run ruff check .` 通过；`uv run pytest` 通过，8 个测试全部通过；`Get-ChildItem src\ui -Recurse -Filter *.py | Select-String "\.backend\."` 无输出；`uv run python -m compileall src tests` 通过；`uv run python -m src.main` 可启动并退出，横幅显示 Step 9；配置源检查确认 `config.model_name` 与 `ChatEngine.model_name` 一致。
- 自动测试覆盖：业务层测试覆盖会话消息读取、中文关键词搜索、英文关键词搜索、空关键词返回空结果、用户隔离和删除会话后的归属校验；TUI 完整交互仍列为人工验证。
- 旧数据影响：不会自动修改旧用户或旧会话中已经记录的历史模型名；修复只影响后续新建用户和新建会话。
- 用户待手工验证项目：新用户和新会话模型名与 ChatEngine 一致；查看有消息和空会话；搜索中文、英文、不存在和空关键词；多个会话分组；用户隔离；Rich 输出无 markup 异常；Step 7/8 对话、加载、重命名和删除功能未回归。
- commit 信息：`feat: step 9 - 对话搜索（E1）+ 查看会话记录 + 模型名 bug 修复`

## Step 10：对话导出与模型切换

- 日期：2026-07-13
- 使用工具：Codex
- 本次任务摘要：实现会话 Markdown 导出、当前用户默认模型设置、当前会话运行时模型切换，并在配置层补全模型注册表。
- Codex 执行内容：检查 Step 9 标签和当前工作区；保留上一轮兼容的 TUI 提示优化；扩展 `config.yaml` 中的模型注册表；完善 ConfigManager、ChatEngine、SessionManager 和 UserManager；在 TUI 会话管理中加入导出入口，在设置菜单加入默认模型设置，在对话视图加入 `/model` 命令。
- 修改文件：`.env.example`、`config.yaml`、`README.md`、`docs/ai_usage_log.md`、`src/core/config_manager.py`、`src/core/chat_engine.py`、`src/core/session_manager.py`、`src/core/user_manager.py`、`src/main.py`、`src/ui/tui/app.py`、`src/ui/tui/chat_view.py`、`src/ui/tui/menu_view.py`、`tests/test_session_manager.py`。
- 关键设计决策：`User.default_model` 和 `Session.model_name` 存储模型别名；ChatEngine 继续无状态，调用时按模型别名解析运行配置；导出路径固定为 `data/users/{username}/exports/`；导出文件名使用安全化用户名、会话标题和日期时间；不修改数据库 schema，不改 `.env`，不提交运行时导出文件。
- 验证命令及结果：`uv sync` 通过；`uv run ruff check .` 通过；`uv run pytest` 通过，8 个测试全部通过；`Get-ChildItem src\ui -Recurse -Filter *.py | Select-String "\.backend\."` 无输出；`uv run python -m src.main` 可启动并退出，横幅显示 Step 10。
- 用户待手工验证项目：在 TUI 设置当前用户默认模型；新建会话使用新默认模型；对话中 `/model` 列表选择和直接别名切换；切换后继续多轮对话且历史上下文保留；会话管理导出 Markdown 并检查文件内容。
- commit 信息：`feat: step 10 - 对话导出与运行时模型切换`

## Step 11：MySQL 异步存储后端与存储切换验证

- 日期：2026-07-13
- 使用工具：Codex
- 本次任务摘要：使用 `aiomysql` 实现 MySQLBackend，支持通过 `StorageFactory` 在 SQLite 与 MySQL 之间切换，并改造初始化脚本按当前配置创建表结构。
- Codex 执行内容：检查 Step 10 标签和干净工作区；通过 `uv add aiomysql` 增加依赖；扩展 MySQL 配置校验；新增 `src/storage/mysql_backend.py`；改造 `StorageFactory` 和 `scripts/init_db.py`；补充可选 MySQL 集成测试；更新 README 和 AI 使用日志。
- 修改文件：`.env.example`、`README.md`、`config.yaml`、`docs/ai_usage_log.md`、`pyproject.toml`、`uv.lock`、`scripts/init_db.py`、`src/core/config_manager.py`、`src/storage/__init__.py`、`src/storage/factory.py`、`src/storage/mysql_backend.py`、`tests/test_mysql_backend.py`。
- 关键设计决策：MySQLBackend 使用连接池和 `utf8mb4`；SQL 使用 `%s` 参数占位符；数据库名使用白名单校验后才拼接；五张表保持与 SQLiteBackend 一致的业务语义；MySQL 集成测试默认跳过，仅在 `RUN_MYSQL_TESTS=1` 且配置独立测试库时启用。
- 验证命令及结果：`uv sync` 通过；`uv run ruff check .` 通过；`uv run pytest` 通过，8 个测试通过、1 个 MySQL 集成测试因未设置 `RUN_MYSQL_TESTS=1` 跳过；`uv run python -c "from src.storage.mysql_backend import MySQLBackend; print(MySQLBackend.__name__)"` 输出 `MySQLBackend`；`uv run python scripts/init_db.py` 在默认 SQLite 配置下成功初始化五张表。
- MySQL 集成测试状态：当前环境未声明可用的外部 MySQL 测试服务，未伪造集成测试通过。
- 用户待手工验证项目：准备 MySQL 服务和测试数据库后设置 `RUN_MYSQL_TESTS=1`、`MYSQL_TEST_DATABASE` 及 MySQL 连接环境变量，运行 MySQL 初始化和集成测试；将 `storage.type` 切换为 `mysql` 后启动 TUI 验证用户、预设、会话、搜索、导出和模型切换流程。
- commit 信息：`feat: step 11 - 实现 MySQL 异步存储后端`

## Step 12：File 后端与结构化日志

- 日期：2026-07-13
- 使用工具：Codex
- Step 12 目标：实现第三种存储后端 `FileBackend`，激活 `storage.type=file`，接入真正 JSONL 文件日志，并为用户、预设、会话、模型调用、存储初始化和 TUI 关键操作补充日志与错误处理。
- 阅读的文档：`D:\study\暑期实训\20260713\docs\需求说明文档.md`、`D:\study\暑期实训\20260713\docs\实施步骤计划.md`、`D:\study\暑期实训\20260713\docs\需求变更与扩展登记.md`、`D:\study\暑期实训\20260713\langchain-docs\langchain-docs\Step12-File后端与日志系统教学文档(1).md`。
- 开始前仓库状态：Git 根目录为 `D:/project/langchain-chat`，当前分支为 `main`，存在 `step-11-mysql` tag；`git status --short` 初始显示 `.env.example`、`pyproject.toml`、`uv.lock` 已有未提交修改，内容为 MySQL 示例账号和 `cryptography` 依赖相关变更，已保留未回退。
- 实际修改文件：`.gitignore`、`config.yaml`、`config/logging.yaml`、`docs/ai_usage_log.md`、`src/core/chat_engine.py`、`src/core/config_manager.py`、`src/core/logging_utils.py`、`src/core/preset_manager.py`、`src/core/session_manager.py`、`src/core/user_manager.py`、`src/main.py`、`src/storage/factory.py`、`src/storage/file_backend.py`、`src/ui/tui/app.py`、`tests/test_file_backend.py`。为满足项目级 `ruff format --check .`，还由 ruff 对 `examples/example3_langchain.py`、`scripts/test_chat_engine.py`、`src/ui/tui/chat_view.py` 做了机械格式化。
- FileBackend 设计：继承当前 `StorageBackend` 的真实 `save_*` 接口；使用 `users.json`、`sessions.json`、`messages.json`、`presets.json`、`user_configs.json` 五个 JSON 文件；根结构固定为列表；datetime 使用 ISO 8601；新增 ID 使用当前最大 ID 加一；文件读写通过 `asyncio.to_thread` 执行；写入使用临时文件 + `os.replace`；JSON 损坏、根结构错误或读写失败会记录日志并向上抛出异常，不静默覆盖原文件；删除用户和会话手动级联；删除预设时置空用户默认预设和会话预设引用；搜索消息先限制在用户会话集合内。
- 日志设计和文档冲突处理：教学文档建议的“伪 JSON”管道格式未采用；按总需求实现 `core.logging_utils.JsonLineFormatter`，文件日志每行是可独立 `json.loads()` 的 JSON 对象，至少包含 `timestamp`、`level`、`logger`、`message`，并按上下文加入 `user_id`、`session_id`、`model`、`status`、`error_type` 等字段。控制台 handler 使用人类可读格式且默认 WARNING+，文件 handler 使用 `TimedRotatingFileHandler` 输出 JSONL。
- 安全处理：日志不输出 `.env` 内容，不主动记录 API Key、Authorization、数据库密码或完整连接字符串；formatter 对敏感 key/文本做基础脱敏；默认不记录完整用户 Prompt、模型回复或 system prompt。
- 实际执行命令及结果：`uv sync` 提权后通过，输出 `Resolved 64 packages`、`Checked 61 packages`；前置 `uv run pytest -q` 提权后通过，结果 `8 passed, 1 skipped`；最终 `uv run python -m compileall src scripts` 通过；`uv run ruff format --check .` 通过，输出 `38 files already formatted`；`uv run ruff check .` 通过，输出 `All checks passed!`；`uv run pytest -q` 通过，输出 `9 passed, 1 skipped`；`git diff --check` 退出码 0，仅有 Windows LF/CRLF 提示。
- FileBackend 独立冒烟验证：使用 `tempfile.TemporaryDirectory()` 临时目录完成 initialize 创建五个文件、创建两个用户、用户名唯一性、创建会话、保存 human/ai 消息、消息顺序、用户隔离搜索、自定义预设、UserConfig、删除会话级联消息、删除用户级联相关数据、close、重新初始化后数据恢复；输出 `FileBackend smoke ok`。
- 日志冒烟验证：使用临时日志文件加载 `config/logging.yaml`，写入 INFO 和可控 ERROR，逐行 `json.loads()` 成功，确认 ERROR 记录存在，确认未出现测试 API Key、Authorization、数据库密码，确认 `httpx`/`langchain` 的 INFO 日志未进入文件；另用 `src.main.setup_logging()` 确认真实 `logs/app.log` 可生成。
- 未完成或需要人工验证项：未执行真实 LLM 调用；未执行交互式 TUI 全流程；未执行 MySQL 集成测试，需具备 MySQL 服务、`RUN_MYSQL_TESTS=1` 和有效测试库环境后人工验证。
- 风险和后续 Step 13 建议：FileBackend 适合教学和小数据量，不具备多进程并发写事务保证；Step 13 可将当前冒烟脚本沉淀为更系统的后端契约测试，并补充日志 formatter 的单元测试、损坏 JSON 文件测试和 StorageFactory 配置错误测试。
- 建议 commit：`feat: step 12 - File 后端与结构化日志`
- 建议 tag：`step-12-logging-file`

## Step 13：核心模块单元测试

- 日期：2026-07-13
- 使用工具：Codex
- Step 13 目标：为 Step 1-12 已实现的核心行为补充稳定、可重复、无外部依赖的自动化测试，重点覆盖存储契约、UserManager、SessionManager 和 ChatEngine，避免后续文档和多环境配置改造破坏现有功能。
- 开始前状态：Git 根目录为 `D:/project/langchain-chat`，当前分支为 `main`，存在 `step-12-logging-file` 标签，开始时 `git status --short` 为空；前置 `uv run pytest -q` 结果为 `9 passed, 1 skipped`，MySQL 集成测试因未设置 `RUN_MYSQL_TESTS=1` 跳过。
- 测试设计：新增共享 fixture，所有默认测试使用 `tmp_path` 下的临时 SQLite 数据库或临时 FileBackend 目录；存储契约测试通过参数化同时运行在 SQLiteBackend 和 FileBackend；MySQL 测试保留显式环境开关，不在默认流程中连接外部 MySQL。
- fixture 设计：`tests/conftest.py` 提供临时 SQLiteBackend、临时 FileBackend、参数化 `storage_backend`、最小用户/会话/消息/预设/UserConfig 工厂、UserManager、SessionManager 和隔离的 `AppConfig`。测试配置使用 `_env_file=None`，并通过 monkeypatch 设置测试专用环境变量，避免读取真实 `.env`。
- Mock 策略：ChatEngine 测试在项目自身 `_get_model` 边界替换为 `FakeModel`，验证非流式、流式、历史消息传递、system prompt 位置、Token usage、超时和异常路径；对 retry/timeout 配置验证采用 monkeypatch `src.core.chat_engine.ChatOpenAI` 捕获构造参数，不调用真实 LLM，也不 patch 第三方私有字段。
- init_db.py 处理：检查确认当前 `scripts/init_db.py` 仅负责根据配置创建存储后端、初始化表/文件结构、输出初始化结果并关闭资源，未发现历史 CRUD 冒烟测试或自动写入演示数据，因此本步骤未修改该脚本。
- 发现并修复的真实缺陷：本步骤未修改生产业务代码。测试层修正了旧 ChatEngine 测试直接调用真实 `get_config()`/构造真实模型的问题，并将旧 SessionManager 测试的 `EnvSettings` 改为 `_env_file=None`，避免单元测试读取真实 `.env`。
- 实际修改文件：`pyproject.toml`、`uv.lock`、`config.yaml`、`docs/ai_usage_log.md`、`tests/conftest.py`、`tests/test_storage.py`、`tests/test_user_manager.py`、`tests/test_preset_manager.py`、`tests/test_session_manager.py`、`tests/test_session_manager_core.py`、`tests/test_chat_engine.py`、`tests/test_chat_engine_core.py`。
- 实际执行命令及真实结果：`uv add --dev pytest-asyncio pytest-cov` 提权后成功，安装 `coverage==7.15.1`、`pytest-asyncio==1.4.0`、`pytest-cov==7.1.0`；中间验证 `uv run pytest -q` 提权后 `61 passed, 1 skipped`；`uv run ruff check tests` 初次失败后仅对本步骤测试文件执行 `uv run ruff check --fix ...`，随后通过。
- 测试数量、通过数量、跳过数量：中间验证为 `61 passed, 1 skipped`；补充 PresetManager 后最终验收结果为 `67 passed, 1 skipped`。
- 覆盖率结果：最终使用 `uv run pytest --cov=src --cov-report=term-missing` 生成真实覆盖率报告，结果见本次最终报告。
- MySQL 测试状态：默认未真实执行 MySQL 集成测试；`tests/test_mysql_backend.py` 继续要求 `RUN_MYSQL_TESTS=1` 和有效测试库配置，当前环境中标记为需要人工环境验证。
- 未验证事项：未调用真实 LLM API；未执行交互式 TUI 人工流程；未连接真实 MySQL Server。
- 风险与 Step 13 后续建议：当前测试重点覆盖核心业务契约，尚未追求高覆盖率门槛；后续可继续补充日志 formatter、StorageFactory 配置错误和 TUI 交互的更细粒度测试，但应放在后续步骤或专项测试中。
- 建议 commit：`test: step 13 - add core module test suite`
- 建议 tag：`step-13-tests`

## Step 14：README、架构文档与扩展预留

- 日期：2026-07-13
- 使用工具：Codex
- Step 14 目标：完善 README 和架构文档，让其他开发者能够安装、配置、运行、测试并理解项目；同时在 UI 接口层预留 WebUI、多模型并行对比、图文/文件、语音和 Tool Calling 的边界，但不实现这些后期功能。
- 开始前状态：Git 根目录为 `D:/project/langchain-chat`，当前分支为 `main`，存在 `step-13-tests` 标签，开始时 `git status --short` 为空；前置 `uv sync` 提权后通过，`uv run pytest -q` 提权后结果为 `67 passed, 1 skipped`。
- README 修改内容：将旧 Step 11 README 刷新为 Step 14 当前状态，覆盖项目定位、功能、技术栈、系统要求、目录结构、快速开始、环境变量、`config.yaml`、三种存储后端、TUI 流程、数据/导出/日志位置、测试和 Ruff 命令、MySQL 集成测试、安全说明、当前限制、后续扩展和 Git Step/tag。
- architecture 内容：新增 `docs/architecture.md`，按真实代码描述分层架构、依赖方向、启动流程、一轮对话流程、实体关系、StorageBackend 与三种实现、StorageFactory 扩展方式、配置与敏感信息边界、JSONL 日志、错误处理、测试 Mock 边界、导出路径、TUI 与未来 WebUI 关系、技术债务和 Step 15 计划。
- 扩展接口设计：在 `src/interface/ui_protocol.py` 中新增独立可选的数据结构和 Protocol，包括 `UITokenUsage`、`UIMessageContext`、`MultiModelCompareRequest`、`SingleModelCompareResult`、`UIAttachmentRef`、语音 STT/TTS 请求与结果、`ToolCallRequest`、`ToolCallUpdate`，以及多模型、附件、语音、工具调用和 WebUI 的 UI 能力协议。
- 保持 TUI 向后兼容的方法：没有给 `AbstractUI` 增加新的抽象方法；当前 `TUIApp` 仍只需要实现原有基础方法，未来能力通过独立 Protocol 按需实现。
- 明确未实现的后期功能：未实现 WebUI、多模型并行调用、图文上传或解析、语音识别/合成、Agent 或 Tool Calling 执行逻辑，也未新增任何 TUI 菜单入口。
- 文档命令验证结果：README 中的 `uv sync`、`uv run python scripts/init_db.py`、`uv run python -m src.main`、`uv run pytest -q`、`uv run pytest --cov=src --cov-report=term-missing`、`uv run ruff check .`、`uv run ruff format --check .` 和 `uv run python -m compileall src` 均与当前入口或工具配置一致；README 未将 Step 15 写成已实现能力。
- 实际测试结果：最终验证命令结果见本次最终报告；MySQL 集成测试默认仍为 skipped，需要 `RUN_MYSQL_TESTS=1` 和有效测试库人工验证。
- 未完成事项：未执行真实 LLM 调用；未运行真实 MySQL 集成测试；未做交互式 TUI 人工全流程；未实现 Step 15 多环境加载。
- 建议 commit：`docs: step 14 - add architecture and extension contracts`
- 建议 tag：`step-14-docs-extend`

## Step 15：dev/test/prod 多环境配置隔离

- 日期：2026-07-14
- 使用工具：Codex
- REQ-001：实现 dev、test、prod 三套业务配置、敏感信息和数据源隔离，通过 `APP_ENV` 一键切换；禁止 prod 回退到 dev。
- 开始前状态：Git 根目录为 `D:/project/langchain-chat`，当前分支为 `main`，存在 `step-14-docs-extend` 标签，开始时 `git status --short` 为空；前置 `uv sync` 通过，前置 `uv run pytest -q` 结果为 `67 passed, 1 skipped`。
- APP_ENV 规则：从进程环境变量读取，未设置默认 `dev`；去除首尾空格并转小写；只允许 `dev`、`test`、`prod`；非法值抛出 `ConfigError`，不静默回退。
- YAML 深度合并：最终配置为 `config.yaml + config.{APP_ENV}.yaml`；mapping 递归合并，scalar 覆盖，list 整体替换；合并函数不修改基础配置对象；缺失或非法 YAML 抛出 `ConfigError`。
- dotenv 选择和优先级：只加载当前 `.env.{env}`，不再默认加载旧 `.env`；使用 `load_dotenv(..., override=False)` 保证操作系统/PowerShell 环境变量优先；不读取其他环境 dotenv 作为回退。
- 三环境数据源设计：dev 使用 `data/dev/sqlite/app.db`；test 使用 `data/test/sqlite/app.db`，自动测试仍优先使用临时目录；prod 使用 MySQL，并通过 `PROD_MYSQL_*` 解析连接信息。
- 新增测试：新增 `tests/test_config_manager.py`，覆盖默认 dev、合法/非法 APP_ENV、深度合并、缺失/非法 YAML、单 dotenv 加载、跨环境 sentinel 隔离、进程环境变量优先、dev/test SQLite 路径隔离、prod mysql 类型、prod 缺失 MySQL 配置失败且不泄露测试密钥、缓存重置后连续切换环境。
- 发现并修复的真实缺陷：prod 使用 `PROD_MYSQL_*` 时，旧版 MySQL 环境解析会使用通用 `EnvSettings` 默认值作为回退，可能掩盖缺失的生产主机/用户/数据库变量；已改为只有旧 `MYSQL_*` 名称才使用旧默认值，环境专属变量必须显式提供。
- 文档更新：README 增加多环境配置、`.env.dev/.env.test/.env.prod` 创建方式、PowerShell/POSIX 切换命令、迁移旧 `.env`、清理 `APP_ENV`、三环境差异和 prod 要求；architecture 增加配置加载顺序、深合并规则、dotenv 选择、进程环境变量优先级、数据源/密钥隔离和 prod 不回退原则。
- 自动验证结果：以最终报告中的真实命令输出为准；默认测试不调用真实 LLM，不连接真实生产数据库。
- dev 人工验证事项：准备 `.env.dev` 后运行初始化、TUI 创建用户、发起对话和导出会话。
- prod 人工验证事项：准备 `.env.prod`、可用 MySQL 和生产模型配置后，运行初始化和核心功能冒烟；本次不伪造真实 MySQL 或 LLM 验收。
- 未通过或未验证项：未执行真实 LLM 调用；未连接真实 MySQL；未进行交互式 TUI 全流程人工验收。
- 建议 commit：`feat: step 15 - add isolated environment configuration`
- 建议 tag：`step-15-envs`，仅在 dev/test/prod 正式验收全部完成后创建。
