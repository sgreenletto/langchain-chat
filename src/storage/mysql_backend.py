"""MySQL storage backend implemented with aiomysql."""

import re
from collections.abc import Awaitable, Callable
from contextlib import AbstractAsyncContextManager
from datetime import datetime
from typing import Any, TypeVar

import aiomysql

try:
    from ..core.config_manager import AppConfig, get_config
    from ..models.schemas import Message, Preset, Session, User, UserConfig
    from .base import StorageBackend
except ImportError:
    from core.config_manager import AppConfig, get_config
    from models.schemas import Message, Preset, Session, User, UserConfig
    from storage.base import StorageBackend

T = TypeVar("T")


class MySQLBackend(StorageBackend):
    """Async MySQL implementation of the StorageBackend contract."""

    def __init__(self, config: AppConfig | None = None) -> None:
        self.config = config or get_config()
        self.mysql_config = self.config.get_mysql_config(require_available=True)
        self._pool: aiomysql.Pool | None = None

    async def initialize(self) -> None:
        """Create database, open the pool, and create required tables."""
        self._validate_database_name(self.mysql_config.database)
        await self._ensure_database()
        self._pool = await aiomysql.create_pool(
            host=self.mysql_config.host,
            port=self.mysql_config.port,
            user=self.mysql_config.user,
            password=self.mysql_config.password,
            db=self.mysql_config.database,
            minsize=self.mysql_config.pool_min_size,
            maxsize=self.mysql_config.pool_max_size,
            charset="utf8mb4",
            autocommit=False,
            cursorclass=aiomysql.DictCursor,
        )
        await self._create_tables()

    async def close(self) -> None:
        """Close the pool safely."""
        if self._pool is None:
            return
        self._pool.close()
        await self._pool.wait_closed()
        self._pool = None

    async def save_user(self, user: User) -> User:
        """Create or update a user."""
        now = self._datetime_to_iso(user.updated_at)

        if user.id > 0 and await self.get_user_by_id(user.id):
            await self._execute_write(
                """
                UPDATE users
                SET username = %s,
                    default_model = %s,
                    default_preset_id = %s,
                    updated_at = %s
                WHERE id = %s
                """,
                (
                    user.username,
                    user.default_model,
                    user.default_preset_id,
                    now,
                    user.id,
                ),
            )
            saved = await self.get_user_by_id(user.id)
            if saved is None:
                raise RuntimeError("保存用户后无法读取数据库记录。")
            return saved

        lastrowid = await self._execute_write(
            """
            INSERT INTO users (
                username, default_model, default_preset_id, created_at, updated_at
            )
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                user.username,
                user.default_model,
                user.default_preset_id,
                self._datetime_to_iso(user.created_at),
                now,
            ),
        )
        saved = None
        if lastrowid is not None and lastrowid > 0:
            saved = await self.get_user_by_id(int(lastrowid))
        if saved is None:
            saved = await self.get_user_by_username(user.username)
        if saved is None:
            raise RuntimeError(
                f"创建用户后无法读取数据库记录：username={user.username!r}, "
                f"lastrowid={lastrowid}"
            )
        return saved

    async def get_user_by_id(self, user_id: int) -> User | None:
        """Return a user by id."""
        row = await self._fetchone("SELECT * FROM users WHERE id = %s", (user_id,))
        return self._row_to_user(row) if row else None

    async def get_user_by_username(self, username: str) -> User | None:
        """Return a user by username."""
        row = await self._fetchone(
            "SELECT * FROM users WHERE username = %s",
            (username,),
        )
        return self._row_to_user(row) if row else None

    async def list_users(self) -> list[User]:
        """List all users."""
        rows = await self._fetchall("SELECT * FROM users ORDER BY id ASC")
        return [self._row_to_user(row) for row in rows]

    async def delete_user(self, user_id: int) -> bool:
        """Delete a user and related data via cascade rules."""
        return await self._execute_delete("DELETE FROM users WHERE id = %s", (user_id,))

    async def save_session(self, session: Session) -> Session:
        """Create or update a session."""
        now = self._datetime_to_iso(session.updated_at)

        if session.id > 0 and await self.get_session(session.id):
            await self._execute_write(
                """
                UPDATE sessions
                SET user_id = %s,
                    title = %s,
                    model_name = %s,
                    preset_id = %s,
                    total_prompt_tokens = %s,
                    total_completion_tokens = %s,
                    updated_at = %s
                WHERE id = %s
                """,
                (
                    session.user_id,
                    session.title,
                    session.model_name,
                    session.preset_id,
                    session.total_prompt_tokens,
                    session.total_completion_tokens,
                    now,
                    session.id,
                ),
            )
            saved = await self.get_session(session.id)
            if saved is None:
                raise RuntimeError("保存会话后无法读取数据库记录。")
            return saved

        lastrowid = await self._execute_write(
            """
            INSERT INTO sessions (
                user_id, title, model_name, preset_id, total_prompt_tokens,
                total_completion_tokens, created_at, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                session.user_id,
                session.title,
                session.model_name,
                session.preset_id,
                session.total_prompt_tokens,
                session.total_completion_tokens,
                self._datetime_to_iso(session.created_at),
                now,
            ),
        )
        if lastrowid is None or lastrowid <= 0:
            raise RuntimeError(f"创建会话后无法获取插入 ID：lastrowid={lastrowid}")
        saved = await self.get_session(int(lastrowid))
        if saved is None:
            raise RuntimeError("创建会话后无法读取数据库记录。")
        return saved

    async def get_session(self, session_id: int) -> Session | None:
        """Return a session by id."""
        row = await self._fetchone(
            "SELECT * FROM sessions WHERE id = %s",
            (session_id,),
        )
        return self._row_to_session(row) if row else None

    async def list_sessions(self, user_id: int) -> list[Session]:
        """List sessions for a user in stable newest-first order."""
        rows = await self._fetchall(
            """
            SELECT * FROM sessions
            WHERE user_id = %s
            ORDER BY updated_at DESC, id DESC
            """,
            (user_id,),
        )
        return [self._row_to_session(row) for row in rows]

    async def delete_session(self, session_id: int) -> bool:
        """Delete a session and related messages."""
        return await self._execute_delete(
            "DELETE FROM sessions WHERE id = %s",
            (session_id,),
        )

    async def save_message(self, message: Message) -> Message:
        """Create or update a message."""
        if message.id > 0:
            existing = await self._fetchone(
                "SELECT id FROM messages WHERE id = %s",
                (message.id,),
            )
            if existing:
                await self._execute_write(
                    """
                    UPDATE messages
                    SET session_id = %s,
                        role = %s,
                        content = %s,
                        prompt_tokens = %s,
                        completion_tokens = %s,
                        created_at = %s
                    WHERE id = %s
                    """,
                    (
                        message.session_id,
                        message.role,
                        message.content,
                        message.prompt_tokens,
                        message.completion_tokens,
                        self._datetime_to_iso(message.created_at),
                        message.id,
                    ),
                )
                row = await self._fetchone(
                    "SELECT * FROM messages WHERE id = %s",
                    (message.id,),
                )
                if row is None:
                    raise RuntimeError("保存消息后无法读取数据库记录。")
                return self._row_to_message(row)

        lastrowid = await self._execute_write(
            """
            INSERT INTO messages (
                session_id, role, content, prompt_tokens, completion_tokens, created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                message.session_id,
                message.role,
                message.content,
                message.prompt_tokens,
                message.completion_tokens,
                self._datetime_to_iso(message.created_at),
            ),
        )
        if lastrowid is None or lastrowid <= 0:
            raise RuntimeError(f"创建消息后无法获取插入 ID：lastrowid={lastrowid}")
        row = await self._fetchone(
            "SELECT * FROM messages WHERE id = %s",
            (int(lastrowid),),
        )
        if row is None:
            raise RuntimeError("创建消息后无法读取数据库记录。")
        return self._row_to_message(row)

    async def list_messages(self, session_id: int) -> list[Message]:
        """List messages for a session in chronological order."""
        rows = await self._fetchall(
            """
            SELECT * FROM messages
            WHERE session_id = %s
            ORDER BY created_at ASC, id ASC
            """,
            (session_id,),
        )
        return [self._row_to_message(row) for row in rows]

    async def search_messages(
        self,
        user_id: int,
        keyword: str,
        limit: int = 20,
    ) -> list[Message]:
        """Search messages for one user."""
        rows = await self._fetchall(
            """
            SELECT messages.*
            FROM messages
            JOIN sessions ON sessions.id = messages.session_id
            WHERE sessions.user_id = %s
              AND messages.content LIKE %s
            ORDER BY messages.created_at ASC, messages.id ASC
            LIMIT %s
            """,
            (user_id, f"%{keyword}%", limit),
        )
        return [self._row_to_message(row) for row in rows]

    async def get_preset_by_id(self, preset_id: int) -> Preset | None:
        """Return any preset by id."""
        row = await self._fetchone("SELECT * FROM presets WHERE id = %s", (preset_id,))
        return self._row_to_preset(row) if row else None

    async def save_preset(self, preset: Preset) -> Preset:
        """Create or update a preset."""
        now = self._datetime_to_iso(preset.updated_at)

        if not preset.id:
            lastrowid = await self._execute_write(
                """
                INSERT INTO presets (
                    user_id, name, description, system_prompt, is_builtin,
                    created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    preset.user_id,
                    preset.name,
                    preset.description,
                    preset.system_prompt,
                    self._bool_to_int(preset.is_builtin),
                    self._datetime_to_iso(preset.created_at),
                    now,
                ),
            )
            saved = None
            if lastrowid is not None and lastrowid > 0:
                saved = await self.get_preset_by_id(int(lastrowid))
            if saved is None:
                saved = await self._get_preset_by_scope_and_name(
                    preset.user_id,
                    preset.name,
                    preset.is_builtin,
                )
            if saved is None:
                raise RuntimeError("创建预设后无法读取数据库记录。")
            return saved

        if await self.get_preset_by_id(preset.id) is None:
            raise RuntimeError(f"要更新的预设不存在：id={preset.id}")

        await self._execute_write(
            """
            UPDATE presets
            SET user_id = %s,
                name = %s,
                description = %s,
                system_prompt = %s,
                is_builtin = %s,
                updated_at = %s
            WHERE id = %s
            """,
            (
                preset.user_id,
                preset.name,
                preset.description,
                preset.system_prompt,
                self._bool_to_int(preset.is_builtin),
                now,
                preset.id,
            ),
        )
        saved = await self.get_preset_by_id(preset.id)
        if saved is None:
            raise RuntimeError("保存预设后无法读取数据库记录。")
        return saved

    async def get_preset(self, preset_id: int) -> Preset | None:
        """Return a preset by id."""
        return await self.get_preset_by_id(preset_id)

    async def _get_preset_by_scope_and_name(
        self,
        user_id: int | None,
        name: str,
        is_builtin: bool,
    ) -> Preset | None:
        """Return the newest matching preset using NULL-safe user scope."""
        if user_id is None:
            row = await self._fetchone(
                """
                SELECT * FROM presets
                WHERE user_id IS NULL
                  AND name = %s
                  AND is_builtin = %s
                ORDER BY id DESC
                LIMIT 1
                """,
                (name, self._bool_to_int(is_builtin)),
            )
        else:
            row = await self._fetchone(
                """
                SELECT * FROM presets
                WHERE user_id = %s
                  AND name = %s
                  AND is_builtin = %s
                ORDER BY id DESC
                LIMIT 1
                """,
                (user_id, name, self._bool_to_int(is_builtin)),
            )
        return self._row_to_preset(row) if row else None

    async def list_presets(self, user_id: int | None = None) -> list[Preset]:
        """List built-in presets and optional user presets."""
        if user_id is None:
            rows = await self._fetchall(
                """
                SELECT * FROM presets
                WHERE user_id IS NULL OR is_builtin = 1
                ORDER BY is_builtin DESC, id ASC
                """
            )
        else:
            rows = await self._fetchall(
                """
                SELECT * FROM presets
                WHERE user_id IS NULL OR is_builtin = 1 OR user_id = %s
                ORDER BY is_builtin DESC, id ASC
                """,
                (user_id,),
            )
        return [self._row_to_preset(row) for row in rows]

    async def delete_preset(self, preset_id: int) -> bool:
        """Delete a preset and null out session references via FK rules."""
        return await self._execute_delete(
            "DELETE FROM presets WHERE id = %s",
            (preset_id,),
        )

    async def save_user_config(self, config: UserConfig) -> UserConfig:
        """Create or update one user config item."""
        if config.id > 0:
            existing = await self._fetchone(
                "SELECT id FROM user_configs WHERE id = %s",
                (config.id,),
            )
            if existing:
                await self._execute_write(
                    """
                    UPDATE user_configs
                    SET user_id = %s,
                        config_key = %s,
                        value = %s,
                        updated_at = %s
                    WHERE id = %s
                    """,
                    (
                        config.user_id,
                        config.key,
                        config.value,
                        self._datetime_to_iso(config.updated_at),
                        config.id,
                    ),
                )
                saved = await self.get_user_config(config.user_id, config.key)
                if saved is None:
                    raise RuntimeError("保存用户配置后无法读取数据库记录。")
                return saved

        await self._execute_write(
            """
            INSERT INTO user_configs (user_id, config_key, value, updated_at)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                value = VALUES(value),
                updated_at = VALUES(updated_at)
            """,
            (
                config.user_id,
                config.key,
                config.value,
                self._datetime_to_iso(config.updated_at),
            ),
        )
        saved = await self.get_user_config(config.user_id, config.key)
        if saved is None:
            raise RuntimeError("保存用户配置后无法读取数据库记录。")
        return saved

    async def get_user_config(self, user_id: int, key: str) -> UserConfig | None:
        """Return one user config item."""
        row = await self._fetchone(
            """
            SELECT * FROM user_configs
            WHERE user_id = %s AND config_key = %s
            """,
            (user_id, key),
        )
        return self._row_to_user_config(row) if row else None

    async def list_user_configs(self, user_id: int) -> list[UserConfig]:
        """List config items for a user."""
        rows = await self._fetchall(
            """
            SELECT * FROM user_configs
            WHERE user_id = %s
            ORDER BY config_key ASC, id ASC
            """,
            (user_id,),
        )
        return [self._row_to_user_config(row) for row in rows]

    async def list_table_names(self) -> list[str]:
        """Return business table names for initialization verification."""
        rows = await self._fetchall(
            """
            SELECT table_name AS name
            FROM information_schema.tables
            WHERE table_schema = DATABASE()
              AND table_name IN (
                  'users', 'sessions', 'messages', 'presets', 'user_configs'
              )
            ORDER BY table_name ASC
            """
        )
        return [str(row["name"]) for row in rows]

    async def _ensure_database(self) -> None:
        connection = await aiomysql.connect(
            host=self.mysql_config.host,
            port=self.mysql_config.port,
            user=self.mysql_config.user,
            password=self.mysql_config.password,
            charset="utf8mb4",
            autocommit=False,
            cursorclass=aiomysql.DictCursor,
        )
        try:
            async with connection.cursor() as cursor:
                await cursor.execute(
                    "CREATE DATABASE IF NOT EXISTS "
                    f"`{self.mysql_config.database}` "
                    "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                )
            await connection.commit()
        except Exception:
            await connection.rollback()
            raise
        finally:
            connection.close()

    async def _create_tables(self) -> None:
        statements = [
            """
            CREATE TABLE IF NOT EXISTS users (
                id BIGINT PRIMARY KEY AUTO_INCREMENT,
                username VARCHAR(191) NOT NULL UNIQUE,
                default_model VARCHAR(191) NULL,
                default_preset_id BIGINT NULL,
                created_at VARCHAR(64) NOT NULL,
                updated_at VARCHAR(64) NOT NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """,
            """
            CREATE TABLE IF NOT EXISTS presets (
                id BIGINT PRIMARY KEY AUTO_INCREMENT,
                user_id BIGINT NULL,
                name VARCHAR(191) NOT NULL,
                description TEXT NOT NULL,
                system_prompt LONGTEXT NOT NULL,
                is_builtin TINYINT NOT NULL DEFAULT 0,
                created_at VARCHAR(64) NOT NULL,
                updated_at VARCHAR(64) NOT NULL,
                CONSTRAINT fk_presets_user_id
                    FOREIGN KEY (user_id)
                    REFERENCES users(id)
                    ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """,
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id BIGINT PRIMARY KEY AUTO_INCREMENT,
                user_id BIGINT NOT NULL,
                title VARCHAR(255) NOT NULL,
                model_name VARCHAR(191) NULL,
                preset_id BIGINT NULL,
                total_prompt_tokens BIGINT NOT NULL DEFAULT 0,
                total_completion_tokens BIGINT NOT NULL DEFAULT 0,
                created_at VARCHAR(64) NOT NULL,
                updated_at VARCHAR(64) NOT NULL,
                CONSTRAINT chk_sessions_prompt_tokens
                    CHECK (total_prompt_tokens >= 0),
                CONSTRAINT chk_sessions_completion_tokens
                    CHECK (total_completion_tokens >= 0),
                CONSTRAINT fk_sessions_user_id
                    FOREIGN KEY (user_id)
                    REFERENCES users(id)
                    ON DELETE CASCADE,
                CONSTRAINT fk_sessions_preset_id
                    FOREIGN KEY (preset_id)
                    REFERENCES presets(id)
                    ON DELETE SET NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """,
            """
            CREATE TABLE IF NOT EXISTS messages (
                id BIGINT PRIMARY KEY AUTO_INCREMENT,
                session_id BIGINT NOT NULL,
                role VARCHAR(16) NOT NULL,
                content LONGTEXT NOT NULL,
                prompt_tokens BIGINT NOT NULL DEFAULT 0,
                completion_tokens BIGINT NOT NULL DEFAULT 0,
                created_at VARCHAR(64) NOT NULL,
                CONSTRAINT chk_messages_role
                    CHECK (role IN ('human', 'ai', 'system')),
                CONSTRAINT chk_messages_prompt_tokens
                    CHECK (prompt_tokens >= 0),
                CONSTRAINT chk_messages_completion_tokens
                    CHECK (completion_tokens >= 0),
                CONSTRAINT fk_messages_session_id
                    FOREIGN KEY (session_id)
                    REFERENCES sessions(id)
                    ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """,
            """
            CREATE TABLE IF NOT EXISTS user_configs (
                id BIGINT PRIMARY KEY AUTO_INCREMENT,
                user_id BIGINT NOT NULL,
                config_key VARCHAR(191) NOT NULL,
                value TEXT NOT NULL,
                updated_at VARCHAR(64) NOT NULL,
                UNIQUE KEY uq_user_configs_user_key (user_id, config_key),
                CONSTRAINT fk_user_configs_user_id
                    FOREIGN KEY (user_id)
                    REFERENCES users(id)
                    ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """,
        ]
        for statement in statements:
            await self._execute_schema(statement)

        await self._add_index_if_missing(
            "sessions",
            "idx_sessions_user_id",
            "CREATE INDEX idx_sessions_user_id ON sessions(user_id)",
        )
        await self._add_index_if_missing(
            "messages",
            "idx_messages_session_id",
            "CREATE INDEX idx_messages_session_id ON messages(session_id)",
        )
        await self._add_index_if_missing(
            "presets",
            "idx_presets_user_id",
            "CREATE INDEX idx_presets_user_id ON presets(user_id)",
        )
        await self._add_index_if_missing(
            "user_configs",
            "idx_user_configs_user_id",
            "CREATE INDEX idx_user_configs_user_id ON user_configs(user_id)",
        )

        await self._add_foreign_key_if_missing(
            "users",
            "fk_users_default_preset_id",
            """
            ALTER TABLE users
            ADD CONSTRAINT fk_users_default_preset_id
                FOREIGN KEY (default_preset_id)
                REFERENCES presets(id)
                ON DELETE SET NULL
            """,
        )

    async def _add_foreign_key_if_missing(
        self,
        table_name: str,
        constraint_name: str,
        statement: str,
    ) -> None:
        row = await self._fetchone(
            """
            SELECT constraint_name
            FROM information_schema.table_constraints
            WHERE table_schema = DATABASE()
              AND table_name = %s
              AND constraint_name = %s
            """,
            (table_name, constraint_name),
        )
        if row is None:
            await self._execute_schema(statement)

    async def _add_index_if_missing(
        self,
        table_name: str,
        index_name: str,
        statement: str,
    ) -> None:
        row = await self._fetchone(
            """
            SELECT index_name
            FROM information_schema.statistics
            WHERE table_schema = DATABASE()
              AND table_name = %s
              AND index_name = %s
            """,
            (table_name, index_name),
        )
        if row is None:
            await self._execute_schema(statement)

    async def _execute_schema(self, sql: str) -> None:
        await self._with_cursor(lambda cursor: cursor.execute(sql))

    async def _execute_write(
        self,
        sql: str,
        parameters: tuple[Any, ...],
    ) -> int | None:
        async def operation(cursor: aiomysql.DictCursor) -> int | None:
            await cursor.execute(sql, parameters)
            if cursor.lastrowid is None:
                return None
            return int(cursor.lastrowid)

        return await self._with_cursor(operation)

    async def _execute_delete(self, sql: str, parameters: tuple[Any, ...]) -> bool:
        async def operation(cursor: aiomysql.DictCursor) -> bool:
            await cursor.execute(sql, parameters)
            return cursor.rowcount > 0

        return await self._with_cursor(operation)

    async def _fetchone(
        self,
        sql: str,
        parameters: tuple[Any, ...] = (),
    ) -> dict[str, Any] | None:
        async with self._acquire() as connection:
            try:
                async with connection.cursor() as cursor:
                    await cursor.execute(sql, parameters)
                    row = await cursor.fetchone()
                await connection.commit()
                return row
            except Exception:
                await connection.rollback()
                raise

    async def _fetchall(
        self,
        sql: str,
        parameters: tuple[Any, ...] = (),
    ) -> list[dict[str, Any]]:
        async with self._acquire() as connection:
            try:
                async with connection.cursor() as cursor:
                    await cursor.execute(sql, parameters)
                    rows = await cursor.fetchall()
                await connection.commit()
                return list(rows)
            except Exception:
                await connection.rollback()
                raise

    async def _with_cursor(
        self,
        operation: Callable[[aiomysql.DictCursor], Awaitable[T]],
    ) -> T:
        async with self._acquire() as connection:
            try:
                async with connection.cursor() as cursor:
                    result = await operation(cursor)
                await connection.commit()
                return result
            except Exception:
                await connection.rollback()
                raise

    def _acquire(self) -> AbstractAsyncContextManager[aiomysql.Connection]:
        if self._pool is None:
            raise RuntimeError("MySQLBackend 尚未初始化，请先调用 initialize()。")
        return self._pool.acquire()

    @staticmethod
    def _validate_database_name(database: str) -> None:
        if not re.fullmatch(r"[A-Za-z0-9_]+", database):
            raise ValueError("MySQL 数据库名只能包含字母、数字和下划线。")

    @staticmethod
    def _datetime_to_iso(value: datetime) -> str:
        return value.isoformat()

    @staticmethod
    def _iso_to_datetime(value: str | datetime) -> datetime:
        if isinstance(value, datetime):
            return value
        return datetime.fromisoformat(value)

    @staticmethod
    def _bool_to_int(value: bool) -> int:
        return 1 if value else 0

    @staticmethod
    def _int_to_bool(value: int | bool) -> bool:
        return bool(value)

    def _row_to_user(self, row: dict[str, Any]) -> User:
        return User(
            id=int(row["id"]),
            username=str(row["username"]),
            default_model=row["default_model"],
            default_preset_id=row["default_preset_id"],
            created_at=self._iso_to_datetime(row["created_at"]),
            updated_at=self._iso_to_datetime(row["updated_at"]),
        )

    def _row_to_session(self, row: dict[str, Any]) -> Session:
        return Session(
            id=int(row["id"]),
            user_id=int(row["user_id"]),
            title=str(row["title"]),
            model_name=row["model_name"],
            preset_id=row["preset_id"],
            total_prompt_tokens=int(row["total_prompt_tokens"]),
            total_completion_tokens=int(row["total_completion_tokens"]),
            created_at=self._iso_to_datetime(row["created_at"]),
            updated_at=self._iso_to_datetime(row["updated_at"]),
        )

    def _row_to_message(self, row: dict[str, Any]) -> Message:
        return Message(
            id=int(row["id"]),
            session_id=int(row["session_id"]),
            role=row["role"],
            content=str(row["content"]),
            prompt_tokens=int(row["prompt_tokens"]),
            completion_tokens=int(row["completion_tokens"]),
            created_at=self._iso_to_datetime(row["created_at"]),
        )

    def _row_to_preset(self, row: dict[str, Any]) -> Preset:
        return Preset(
            id=int(row["id"]),
            user_id=row["user_id"],
            name=str(row["name"]),
            description=str(row["description"]),
            system_prompt=str(row["system_prompt"]),
            is_builtin=self._int_to_bool(row["is_builtin"]),
            created_at=self._iso_to_datetime(row["created_at"]),
            updated_at=self._iso_to_datetime(row["updated_at"]),
        )

    def _row_to_user_config(self, row: dict[str, Any]) -> UserConfig:
        return UserConfig(
            id=int(row["id"]),
            user_id=int(row["user_id"]),
            key=str(row["config_key"]),
            value=str(row["value"]),
            updated_at=self._iso_to_datetime(row["updated_at"]),
        )
