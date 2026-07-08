"""
core/state_db.py — SQLite 状态数据库

记录每个源文件的转换状态、哈希、输出路径等信息，支持断点恢复和重试。
"""

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator, Optional


# ------------------------------------------------------------------
# 数据模型
# ------------------------------------------------------------------

@dataclass
class SyncRecord:
    source_path: str
    source_hash: Optional[str] = None
    output_path: Optional[str] = None
    converter: Optional[str] = None
    status: str = "pending"          # pending | ok | failed | source_deleted
    error_msg: Optional[str] = None
    converted_at: Optional[str] = None
    last_sync: Optional[str] = None
    retry_count: int = 0
    id: Optional[int] = field(default=None, repr=False)


# ------------------------------------------------------------------
# DDL
# ------------------------------------------------------------------

_DDL = """
CREATE TABLE IF NOT EXISTS sync_state (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source_path     TEXT    UNIQUE NOT NULL,
    source_hash     TEXT,
    output_path     TEXT,
    converter       TEXT,
    status          TEXT    NOT NULL DEFAULT 'pending',
    error_msg       TEXT,
    converted_at    TEXT,
    last_sync       TEXT,
    retry_count     INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_status ON sync_state(status);
CREATE INDEX IF NOT EXISTS idx_last_sync ON sync_state(last_sync);
"""


# ------------------------------------------------------------------
# 数据库管理类
# ------------------------------------------------------------------

class StateDB:
    """线程安全的 SQLite 状态数据库封装。"""

    def __init__(self, db_path: Path) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db_path = str(db_path)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")   # 提高并发写入性能
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    @contextmanager
    def _cursor(self) -> Generator[sqlite3.Cursor, None, None]:
        conn = self._connect()
        try:
            cur = conn.cursor()
            yield cur
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._cursor() as cur:
            cur.executescript(_DDL)

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def get(self, source_path: str) -> Optional[SyncRecord]:
        """按源文件路径查询记录。"""
        with self._cursor() as cur:
            cur.execute("SELECT * FROM sync_state WHERE source_path = ?", (source_path,))
            row = cur.fetchone()
            return _row_to_record(row) if row else None

    def upsert(self, record: SyncRecord) -> None:
        """插入或更新一条记录。"""
        now = _now_iso()
        with self._cursor() as cur:
            cur.execute(
                """
                INSERT INTO sync_state
                    (source_path, source_hash, output_path, converter,
                     status, error_msg, converted_at, last_sync, retry_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(source_path) DO UPDATE SET
                    source_hash  = excluded.source_hash,
                    output_path  = excluded.output_path,
                    converter    = excluded.converter,
                    status       = excluded.status,
                    error_msg    = excluded.error_msg,
                    converted_at = excluded.converted_at,
                    last_sync    = ?,
                    retry_count  = excluded.retry_count
                """,
                (
                    record.source_path,
                    record.source_hash,
                    record.output_path,
                    record.converter,
                    record.status,
                    record.error_msg,
                    record.converted_at,
                    now,
                    record.retry_count,
                    now,   # last_sync in UPDATE
                ),
            )

    def mark_status(
        self,
        source_path: str,
        status: str,
        error_msg: Optional[str] = None,
    ) -> None:
        """仅更新状态字段。"""
        with self._cursor() as cur:
            cur.execute(
                """
                UPDATE sync_state
                SET status = ?, error_msg = ?, last_sync = ?
                WHERE source_path = ?
                """,
                (status, error_msg, _now_iso(), source_path),
            )

    def increment_retry(self, source_path: str) -> int:
        """重试计数 +1，返回新的计数值。"""
        with self._cursor() as cur:
            cur.execute(
                "UPDATE sync_state SET retry_count = retry_count + 1 WHERE source_path = ?",
                (source_path,),
            )
            cur.execute(
                "SELECT retry_count FROM sync_state WHERE source_path = ?",
                (source_path,),
            )
            row = cur.fetchone()
            return row["retry_count"] if row else 0

    def rename(self, old_path: str, new_path: str) -> None:
        """处理源文件重命名。"""
        with self._cursor() as cur:
            cur.execute(
                "UPDATE sync_state SET source_path = ?, last_sync = ? WHERE source_path = ?",
                (new_path, _now_iso(), old_path),
            )

    def list_pending_retry(self, max_retries: int) -> list[SyncRecord]:
        """获取需要重试的失败记录。"""
        with self._cursor() as cur:
            cur.execute(
                """
                SELECT * FROM sync_state
                WHERE status = 'failed' AND retry_count < ?
                ORDER BY last_sync ASC
                """,
                (max_retries,),
            )
            return [_row_to_record(row) for row in cur.fetchall()]

    def list_all(self) -> list[SyncRecord]:
        """获取所有记录（用于状态报告）。"""
        with self._cursor() as cur:
            cur.execute("SELECT * FROM sync_state ORDER BY last_sync DESC")
            return [_row_to_record(row) for row in cur.fetchall()]

    def stats(self) -> dict[str, int]:
        """返回各状态的数量统计。"""
        with self._cursor() as cur:
            cur.execute(
                "SELECT status, COUNT(*) as cnt FROM sync_state GROUP BY status"
            )
            return {row["status"]: row["cnt"] for row in cur.fetchall()}


# ------------------------------------------------------------------
# 内部工具
# ------------------------------------------------------------------

def _row_to_record(row: sqlite3.Row) -> SyncRecord:
    return SyncRecord(
        id=row["id"],
        source_path=row["source_path"],
        source_hash=row["source_hash"],
        output_path=row["output_path"],
        converter=row["converter"],
        status=row["status"],
        error_msg=row["error_msg"],
        converted_at=row["converted_at"],
        last_sync=row["last_sync"],
        retry_count=row["retry_count"],
    )


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()
