"""SQLite 数据库初始化与连接。

数据库文件：~/.api-tool/api-tool.db
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path

from backend.app.config import CONFIG_DIR

DB_PATH = CONFIG_DIR / "api-tool.db"


def _get_conn() -> sqlite3.Connection:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    # WAL 模式：读写不互相阻塞，适合多用户同时用
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def get_db():
    conn = _get_conn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    with get_db() as conn:
        # 迁移：旧版 collections 表没有 team_id 列，直接重建（开发阶段数据可丢）
        cols = [r[1] for r in conn.execute("PRAGMA table_info(collections)").fetchall()]
        if cols and "team_id" not in cols:
            conn.execute("DROP TABLE collections")

        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                display_name TEXT NOT NULL,
                -- 头像：data:image/...;base64,... 形式，前端已压缩到 20KB 以内
                avatar TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                expires_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS teams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                owner_id INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS team_members (
                team_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                role TEXT NOT NULL DEFAULT 'member',
                joined_at TEXT NOT NULL DEFAULT (datetime('now')),
                PRIMARY KEY (team_id, user_id),
                FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS collections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                team_id INTEGER,
                tree_json TEXT NOT NULL DEFAULT '[]',
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                CHECK ((user_id IS NOT NULL AND team_id IS NULL) OR (user_id IS NULL AND team_id IS NOT NULL)),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_collections_user ON collections(user_id);
            CREATE INDEX IF NOT EXISTS idx_collections_team ON collections(team_id);
            CREATE UNIQUE INDEX IF NOT EXISTS uq_collections_user ON collections(user_id) WHERE user_id IS NOT NULL;
            CREATE UNIQUE INDEX IF NOT EXISTS uq_collections_team ON collections(team_id) WHERE team_id IS NOT NULL;
            CREATE INDEX IF NOT EXISTS idx_team_members_user ON team_members(user_id);

            CREATE TABLE IF NOT EXISTS http_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                method TEXT NOT NULL,
                url TEXT NOT NULL,
                headers_json TEXT NOT NULL DEFAULT '[]',
                body_type TEXT NOT NULL DEFAULT 'json',
                body TEXT,
                status_code INTEGER,
                elapsed_ms INTEGER,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS mcp_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                server TEXT NOT NULL,
                tool TEXT NOT NULL,
                args_json TEXT NOT NULL DEFAULT '{}',
                is_error INTEGER NOT NULL DEFAULT 0,
                content TEXT,
                error TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS llm_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                provider TEXT NOT NULL,
                model TEXT NOT NULL,
                messages_json TEXT NOT NULL DEFAULT '[]',
                content TEXT,
                finish_reason TEXT,
                usage_json TEXT NOT NULL DEFAULT '{}',
                stream INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_http_history_user ON http_history(user_id, id DESC);
            CREATE INDEX IF NOT EXISTS idx_mcp_history_user ON mcp_history(user_id, id DESC);
            CREATE INDEX IF NOT EXISTS idx_llm_history_user ON llm_history(user_id, id DESC);

            CREATE TABLE IF NOT EXISTS bench_jobs (
                id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'running',
                total INTEGER NOT NULL DEFAULT 0,
                done INTEGER NOT NULL DEFAULT 0,
                success INTEGER NOT NULL DEFAULT 0,
                fail INTEGER NOT NULL DEFAULT 0,
                concurrency INTEGER NOT NULL DEFAULT 10,
                streaming INTEGER NOT NULL DEFAULT 0,
                columns_json TEXT NOT NULL DEFAULT '[]',
                -- 所属接口标识：node:<集合节点id> 或 req:<METHOD>:<url>，用于按接口过滤任务记录
                scope_key TEXT NOT NULL DEFAULT '',
                -- 数据来源快照（测试集 id / 名称 / 内容哈希），用于追踪历史用的是哪一版测试集
                dataset_id TEXT NOT NULL DEFAULT '',
                dataset_name TEXT NOT NULL DEFAULT '',
                dataset_hash TEXT NOT NULL DEFAULT '',
                -- 参数文件 / 结果文件的绝对路径
                params_path TEXT NOT NULL DEFAULT '',
                result_path TEXT NOT NULL DEFAULT '',
                error TEXT NOT NULL DEFAULT '',
                avg_ms REAL NOT NULL DEFAULT 0,
                p95_ms REAL NOT NULL DEFAULT 0,
                ttft_avg_ms REAL NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_bench_jobs_user ON bench_jobs(user_id, created_at DESC);

            CREATE TABLE IF NOT EXISTS bench_datasets (
                id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                -- CSV 表头（占位符列名）与数据行数
                columns_json TEXT NOT NULL DEFAULT '[]',
                rows INTEGER NOT NULL DEFAULT 0,
                -- 测试集文件绝对路径
                path TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_bench_datasets_user ON bench_datasets(user_id, created_at DESC);

            CREATE TABLE IF NOT EXISTS secrets (
                id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                value TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                UNIQUE(user_id, name),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_secrets_user ON secrets(user_id, name);
            """
        )
        # 为已存在但没有集合行的用户补一条空的个人空间
        conn.execute(
            """INSERT INTO collections (user_id, team_id, tree_json)
               SELECT u.id, NULL, '[]' FROM users u
               WHERE NOT EXISTS (SELECT 1 FROM collections c WHERE c.user_id = u.id)"""
        )

        # 迁移：旧版 users 表没有 avatar 列
        user_cols = [r[1] for r in conn.execute("PRAGMA table_info(users)").fetchall()]
        if user_cols and "avatar" not in user_cols:
            conn.execute("ALTER TABLE users ADD COLUMN avatar TEXT NOT NULL DEFAULT ''")

        # 迁移：旧版 bench_jobs 没有 scope_key 列（老记录留空，只在"全部接口"视图里可见）
        bench_cols = [r[1] for r in conn.execute("PRAGMA table_info(bench_jobs)").fetchall()]
        if bench_cols and "scope_key" not in bench_cols:
            conn.execute("ALTER TABLE bench_jobs ADD COLUMN scope_key TEXT NOT NULL DEFAULT ''")

        # 迁移：旧版 bench_jobs 没有测试集快照信息（dataset_id / dataset_name / dataset_hash）
        if bench_cols:
            for col in ("dataset_id", "dataset_name", "dataset_hash"):
                if col not in bench_cols:
                    conn.execute(
                        f"ALTER TABLE bench_jobs ADD COLUMN {col} TEXT NOT NULL DEFAULT ''"
                    )


__all__ = ["DB_PATH", "get_db", "init_db"]
