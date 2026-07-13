"""SQLite storage backend implemented with aiosqlite."""

from datetime import datetime
from pathlib import Path
from typing import Any

import aiosqlite

from core.config_manager import get_config
from models.schemas import Message, Preset, Session, User, UserConfig
from storage.base import StorageBackend


class SQLiteBackend(StorageBackend):
    """Async SQLite implementation of the StorageBackend contract."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        config = get_config()
        configured_path = db_path or config.storage.sqlite.database_path
        path = Path(configured_path)
        if not path.is_absolute():
            path = config.project_root / path

        self.db_path = path
        self._connection: aiosqlite.Connection | None = None

    async def initialize(self) -> None:
        """Open the database connection and create required tables."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = await aiosqlite.connect(self.db_path)
        self._connection.row_factory = aiosqlite.Row
        await self._connection.execute("PRAGMA foreign_keys = ON")
        await self._create_tables()
        await self._connection.commit()

    async def close(self) -> None:
        """Close the connection safely."""
        if self._connection is not None:
            await self._connection.close()
            self._connection = None

    async def save_user(self, user: User) -> User:
        """Create or update a user."""
        connection = self._require_connection()
        now = self._datetime_to_iso(user.updated_at)

        if user.id > 0 and await self.get_user_by_id(user.id):
            await connection.execute(
                """
                UPDATE users
                SET username = ?,
                    default_model = ?,
                    default_preset_id = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    user.username,
                    user.default_model,
                    user.default_preset_id,
                    now,
                    user.id,
                ),
            )
            await connection.commit()
            saved = await self.get_user_by_id(user.id)
            if saved is None:
                raise RuntimeError("保存用户后无法读取数据库记录。")
            return saved

        cursor = await connection.execute(
            """
            INSERT INTO users (
                username, default_model, default_preset_id, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                user.username,
                user.default_model,
                user.default_preset_id,
                self._datetime_to_iso(user.created_at),
                now,
            ),
        )
        await connection.commit()
        saved = await self.get_user_by_id(int(cursor.lastrowid))
        if saved is None:
            raise RuntimeError("创建用户后无法读取数据库记录。")
        return saved

    async def get_user_by_id(self, user_id: int) -> User | None:
        """Return a user by id."""
        row = await self._fetchone("SELECT * FROM users WHERE id = ?", (user_id,))
        return self._row_to_user(row) if row else None

    async def get_user_by_username(self, username: str) -> User | None:
        """Return a user by username."""
        row = await self._fetchone(
            "SELECT * FROM users WHERE username = ?",
            (username,),
        )
        return self._row_to_user(row) if row else None

    async def list_users(self) -> list[User]:
        """List all users."""
        rows = await self._fetchall("SELECT * FROM users ORDER BY id ASC")
        return [self._row_to_user(row) for row in rows]

    async def delete_user(self, user_id: int) -> bool:
        """Delete a user and related data via cascade rules."""
        connection = self._require_connection()
        cursor = await connection.execute("DELETE FROM users WHERE id = ?", (user_id,))
        await connection.commit()
        return cursor.rowcount > 0

    async def save_session(self, session: Session) -> Session:
        """Create or update a session."""
        connection = self._require_connection()
        now = self._datetime_to_iso(session.updated_at)

        if session.id > 0 and await self.get_session(session.id):
            await connection.execute(
                """
                UPDATE sessions
                SET user_id = ?,
                    title = ?,
                    model_name = ?,
                    preset_id = ?,
                    total_prompt_tokens = ?,
                    total_completion_tokens = ?,
                    updated_at = ?
                WHERE id = ?
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
            await connection.commit()
            saved = await self.get_session(session.id)
            if saved is None:
                raise RuntimeError("保存会话后无法读取数据库记录。")
            return saved

        cursor = await connection.execute(
            """
            INSERT INTO sessions (
                user_id, title, model_name, preset_id, total_prompt_tokens,
                total_completion_tokens, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
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
        await connection.commit()
        saved = await self.get_session(int(cursor.lastrowid))
        if saved is None:
            raise RuntimeError("创建会话后无法读取数据库记录。")
        return saved

    async def get_session(self, session_id: int) -> Session | None:
        """Return a session by id."""
        row = await self._fetchone("SELECT * FROM sessions WHERE id = ?", (session_id,))
        return self._row_to_session(row) if row else None

    async def list_sessions(self, user_id: int) -> list[Session]:
        """List sessions for a user in stable newest-first order."""
        rows = await self._fetchall(
            """
            SELECT * FROM sessions
            WHERE user_id = ?
            ORDER BY updated_at DESC, id DESC
            """,
            (user_id,),
        )
        return [self._row_to_session(row) for row in rows]

    async def delete_session(self, session_id: int) -> bool:
        """Delete a session and related messages."""
        connection = self._require_connection()
        cursor = await connection.execute(
            "DELETE FROM sessions WHERE id = ?",
            (session_id,),
        )
        await connection.commit()
        return cursor.rowcount > 0

    async def save_message(self, message: Message) -> Message:
        """Create or update a message."""
        connection = self._require_connection()

        if message.id > 0:
            existing = await self._fetchone(
                "SELECT id FROM messages WHERE id = ?",
                (message.id,),
            )
            if existing:
                await connection.execute(
                    """
                    UPDATE messages
                    SET session_id = ?,
                        role = ?,
                        content = ?,
                        prompt_tokens = ?,
                        completion_tokens = ?,
                        created_at = ?
                    WHERE id = ?
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
                await connection.commit()
                row = await self._fetchone(
                    "SELECT * FROM messages WHERE id = ?",
                    (message.id,),
                )
                if row is None:
                    raise RuntimeError("保存消息后无法读取数据库记录。")
                return self._row_to_message(row)

        cursor = await connection.execute(
            """
            INSERT INTO messages (
                session_id, role, content, prompt_tokens, completion_tokens, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
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
        await connection.commit()
        row = await self._fetchone(
            "SELECT * FROM messages WHERE id = ?",
            (int(cursor.lastrowid),),
        )
        if row is None:
            raise RuntimeError("创建消息后无法读取数据库记录。")
        return self._row_to_message(row)

    async def list_messages(self, session_id: int) -> list[Message]:
        """List messages for a session in chronological order."""
        rows = await self._fetchall(
            """
            SELECT * FROM messages
            WHERE session_id = ?
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
            WHERE sessions.user_id = ?
              AND messages.content LIKE ?
            ORDER BY messages.created_at ASC, messages.id ASC
            LIMIT ?
            """,
            (user_id, f"%{keyword}%", limit),
        )
        return [self._row_to_message(row) for row in rows]

    async def save_preset(self, preset: Preset) -> Preset:
        """Create or update a preset."""
        connection = self._require_connection()
        now = self._datetime_to_iso(preset.updated_at)

        if preset.id > 0 and await self.get_preset(preset.id):
            await connection.execute(
                """
                UPDATE presets
                SET user_id = ?,
                    name = ?,
                    description = ?,
                    system_prompt = ?,
                    is_builtin = ?,
                    updated_at = ?
                WHERE id = ?
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
            await connection.commit()
            saved = await self.get_preset(preset.id)
            if saved is None:
                raise RuntimeError("保存预设后无法读取数据库记录。")
            return saved

        cursor = await connection.execute(
            """
            INSERT INTO presets (
                user_id, name, description, system_prompt, is_builtin,
                created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
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
        await connection.commit()
        saved = await self.get_preset(int(cursor.lastrowid))
        if saved is None:
            raise RuntimeError("创建预设后无法读取数据库记录。")
        return saved

    async def get_preset(self, preset_id: int) -> Preset | None:
        """Return a preset by id."""
        row = await self._fetchone("SELECT * FROM presets WHERE id = ?", (preset_id,))
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
                WHERE user_id IS NULL OR is_builtin = 1 OR user_id = ?
                ORDER BY is_builtin DESC, id ASC
                """,
                (user_id,),
            )
        return [self._row_to_preset(row) for row in rows]

    async def delete_preset(self, preset_id: int) -> bool:
        """Delete a preset and null out session references via FK rules."""
        connection = self._require_connection()
        cursor = await connection.execute(
            "DELETE FROM presets WHERE id = ?",
            (preset_id,),
        )
        await connection.commit()
        return cursor.rowcount > 0

    async def save_user_config(self, config: UserConfig) -> UserConfig:
        """Create or update one user config item."""
        connection = self._require_connection()

        if config.id > 0:
            existing = await self._fetchone(
                "SELECT id FROM user_configs WHERE id = ?",
                (config.id,),
            )
            if existing:
                await connection.execute(
                    """
                    UPDATE user_configs
                    SET user_id = ?,
                        key = ?,
                        value = ?,
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        config.user_id,
                        config.key,
                        config.value,
                        self._datetime_to_iso(config.updated_at),
                        config.id,
                    ),
                )
                await connection.commit()
                saved = await self.get_user_config(config.user_id, config.key)
                if saved is None:
                    raise RuntimeError("保存用户配置后无法读取数据库记录。")
                return saved

        await connection.execute(
            """
            INSERT INTO user_configs (user_id, key, value, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, key)
            DO UPDATE SET value = excluded.value,
                          updated_at = excluded.updated_at
            """,
            (
                config.user_id,
                config.key,
                config.value,
                self._datetime_to_iso(config.updated_at),
            ),
        )
        await connection.commit()
        saved = await self.get_user_config(config.user_id, config.key)
        if saved is None:
            raise RuntimeError("保存用户配置后无法读取数据库记录。")
        return saved

    async def get_user_config(self, user_id: int, key: str) -> UserConfig | None:
        """Return one user config item."""
        row = await self._fetchone(
            """
            SELECT * FROM user_configs
            WHERE user_id = ? AND key = ?
            """,
            (user_id, key),
        )
        return self._row_to_user_config(row) if row else None

    async def list_user_configs(self, user_id: int) -> list[UserConfig]:
        """List config items for a user."""
        rows = await self._fetchall(
            """
            SELECT * FROM user_configs
            WHERE user_id = ?
            ORDER BY key ASC, id ASC
            """,
            (user_id,),
        )
        return [self._row_to_user_config(row) for row in rows]

    async def list_table_names(self) -> list[str]:
        """Return business table names for initialization verification."""
        rows = await self._fetchall(
            """
            SELECT name FROM sqlite_master
            WHERE type = 'table'
              AND name IN ('users', 'sessions', 'messages', 'presets', 'user_configs')
            ORDER BY name ASC
            """
        )
        return [str(row["name"]) for row in rows]

    async def _create_tables(self) -> None:
        connection = self._require_connection()
        await connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                default_model TEXT,
                default_preset_id INTEGER,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (default_preset_id)
                    REFERENCES presets(id)
                    ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS presets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                name TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                system_prompt TEXT NOT NULL,
                is_builtin INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (user_id)
                    REFERENCES users(id)
                    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                model_name TEXT,
                preset_id INTEGER,
                total_prompt_tokens INTEGER NOT NULL DEFAULT 0 CHECK (
                    total_prompt_tokens >= 0
                ),
                total_completion_tokens INTEGER NOT NULL DEFAULT 0 CHECK (
                    total_completion_tokens >= 0
                ),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (user_id)
                    REFERENCES users(id)
                    ON DELETE CASCADE,
                FOREIGN KEY (preset_id)
                    REFERENCES presets(id)
                    ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                role TEXT NOT NULL CHECK (role IN ('human', 'ai', 'system')),
                content TEXT NOT NULL,
                prompt_tokens INTEGER NOT NULL DEFAULT 0 CHECK (prompt_tokens >= 0),
                completion_tokens INTEGER NOT NULL DEFAULT 0 CHECK (
                    completion_tokens >= 0
                ),
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id)
                    REFERENCES sessions(id)
                    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS user_configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(user_id, key),
                FOREIGN KEY (user_id)
                    REFERENCES users(id)
                    ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_sessions_user_id
                ON sessions(user_id);
            CREATE INDEX IF NOT EXISTS idx_messages_session_id
                ON messages(session_id);
            CREATE INDEX IF NOT EXISTS idx_presets_user_id
                ON presets(user_id);
            CREATE INDEX IF NOT EXISTS idx_user_configs_user_id
                ON user_configs(user_id);
            """
        )

    def _require_connection(self) -> aiosqlite.Connection:
        if self._connection is None:
            raise RuntimeError("SQLiteBackend 尚未初始化，请先调用 initialize()。")
        return self._connection

    async def _fetchone(
        self,
        sql: str,
        parameters: tuple[Any, ...] = (),
    ) -> aiosqlite.Row | None:
        connection = self._require_connection()
        cursor = await connection.execute(sql, parameters)
        return await cursor.fetchone()

    async def _fetchall(
        self,
        sql: str,
        parameters: tuple[Any, ...] = (),
    ) -> list[aiosqlite.Row]:
        connection = self._require_connection()
        cursor = await connection.execute(sql, parameters)
        rows = await cursor.fetchall()
        return list(rows)

    @staticmethod
    def _datetime_to_iso(value: datetime) -> str:
        return value.isoformat()

    @staticmethod
    def _iso_to_datetime(value: str) -> datetime:
        return datetime.fromisoformat(value)

    @staticmethod
    def _bool_to_int(value: bool) -> int:
        return 1 if value else 0

    @staticmethod
    def _int_to_bool(value: int) -> bool:
        return bool(value)

    def _row_to_user(self, row: aiosqlite.Row) -> User:
        return User(
            id=int(row["id"]),
            username=str(row["username"]),
            default_model=row["default_model"],
            default_preset_id=row["default_preset_id"],
            created_at=self._iso_to_datetime(str(row["created_at"])),
            updated_at=self._iso_to_datetime(str(row["updated_at"])),
        )

    def _row_to_session(self, row: aiosqlite.Row) -> Session:
        return Session(
            id=int(row["id"]),
            user_id=int(row["user_id"]),
            title=str(row["title"]),
            model_name=row["model_name"],
            preset_id=row["preset_id"],
            total_prompt_tokens=int(row["total_prompt_tokens"]),
            total_completion_tokens=int(row["total_completion_tokens"]),
            created_at=self._iso_to_datetime(str(row["created_at"])),
            updated_at=self._iso_to_datetime(str(row["updated_at"])),
        )

    def _row_to_message(self, row: aiosqlite.Row) -> Message:
        return Message(
            id=int(row["id"]),
            session_id=int(row["session_id"]),
            role=row["role"],
            content=str(row["content"]),
            prompt_tokens=int(row["prompt_tokens"]),
            completion_tokens=int(row["completion_tokens"]),
            created_at=self._iso_to_datetime(str(row["created_at"])),
        )

    def _row_to_preset(self, row: aiosqlite.Row) -> Preset:
        return Preset(
            id=int(row["id"]),
            user_id=row["user_id"],
            name=str(row["name"]),
            description=str(row["description"]),
            system_prompt=str(row["system_prompt"]),
            is_builtin=self._int_to_bool(int(row["is_builtin"])),
            created_at=self._iso_to_datetime(str(row["created_at"])),
            updated_at=self._iso_to_datetime(str(row["updated_at"])),
        )

    def _row_to_user_config(self, row: aiosqlite.Row) -> UserConfig:
        return UserConfig(
            id=int(row["id"]),
            user_id=int(row["user_id"]),
            key=str(row["key"]),
            value=str(row["value"]),
            updated_at=self._iso_to_datetime(str(row["updated_at"])),
        )
