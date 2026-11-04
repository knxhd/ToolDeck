"""批量测试持久化：任务记录进 SQLite，参数/结果文件按 接口名_时间 分目录存放。

目录布局（与 api-tool.db 同目录）：
    <CONFIG_DIR>/
        api-tool.db
        benchmark/
            _staging/<upload_id>.csv                 上传临时区（发起任务后归档删除）
            <接口名>_<时间>/
                params_<时间>.csv                    参数文件
                result_<时间>.csv                    结果文件
"""
from __future__ import annotations

import json
import re
import shutil
import time
import uuid
from pathlib import Path

from backend.app.config import CONFIG_DIR
from backend.app.services.db import get_db

MAX_FILE_BYTES = 10 * 1024 * 1024  # 10MB

_BENCH_ROOT = CONFIG_DIR / "benchmark"
_STAGING_DIR = _BENCH_ROOT / "_staging"


def _ensure_dirs() -> None:
    _STAGING_DIR.mkdir(parents=True, exist_ok=True)


def timestamp() -> str:
    """文件名/目录用时间串：YYYYmmdd_HHMMSS。"""
    return time.strftime("%Y%m%d_%H%M%S", time.localtime())


def _sanitize(name: str) -> str:
    """去掉文件系统非法字符，保留可读部分。"""
    cleaned = re.sub(r'[\\/:*?"<>|\s]+', "_", (name or "").strip()).strip("_")
    return cleaned[:60] or "job"


def new_upload_id() -> str:
    return uuid.uuid4().hex[:12]


def new_job_id() -> str:
    return uuid.uuid4().hex[:12]


# ---------- 上传临时区 ----------

def staging_path(upload_id: str) -> Path:
    _ensure_dirs()
    return _STAGING_DIR / f"{upload_id}.csv"


def save_staging(upload_id: str, raw: bytes) -> Path:
    p = staging_path(upload_id)
    p.write_bytes(raw)
    return p


def read_staging(upload_id: str) -> bytes:
    return staging_path(upload_id).read_bytes()


def delete_staging(upload_id: str) -> None:
    staging_path(upload_id).unlink(missing_ok=True)


# ---------- 任务目录与文件 ----------

def create_job_folder(name: str, ts: str) -> tuple[Path, Path, Path]:
    """创建 <接口名>_<时间>/ 目录，返回 (目录, 参数文件路径, 结果文件路径)。"""
    folder = _BENCH_ROOT / f"{_sanitize(name)}_{ts}"
    folder.mkdir(parents=True, exist_ok=True)
    params = folder / f"params_{ts}.csv"
    result = folder / f"result_{ts}.csv"
    return folder, params, result


def import_staging_to_params(upload_id: str, params_path: Path) -> None:
    """把上传临时文件移动为任务的参数文件。"""
    shutil.move(str(staging_path(upload_id)), str(params_path))


# ---------- 任务记录（SQLite） ----------

def insert_job(fields: dict) -> None:
    cols = ", ".join(fields.keys())
    ph = ", ".join(f":{k}" for k in fields.keys())
    with get_db() as conn:
        conn.execute(f"INSERT INTO bench_jobs ({cols}) VALUES ({ph})", fields)


def _row_to_dict(row) -> dict:
    d = dict(row)
    d["streaming"] = bool(d.get("streaming"))
    try:
        d["columns"] = json.loads(d.get("columns_json") or "[]")
    except json.JSONDecodeError:
        d["columns"] = []
    d.pop("columns_json", None)
    d["stats"] = {
        "avg_ms": d.pop("avg_ms", 0) or 0,
        "p95_ms": d.pop("p95_ms", 0) or 0,
        "ttft_avg_ms": d.pop("ttft_avg_ms", 0) or 0,
    }
    return d


def list_jobs(user_id: int) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM bench_jobs WHERE user_id=? ORDER BY created_at DESC LIMIT 200",
            (user_id,),
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_job(job_id: str, user_id: int) -> dict | None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM bench_jobs WHERE id=? AND user_id=?", (job_id, user_id)
        ).fetchone()
    return _row_to_dict(row) if row else None


def update_job(job_id: str, user_id: int, **fields) -> None:
    if not fields:
        return
    set_clause = ", ".join(f"{k}=:{k}" for k in fields)
    fields["id"] = job_id
    fields["user_id"] = user_id
    with get_db() as conn:
        conn.execute(
            f"UPDATE bench_jobs SET {set_clause} WHERE id=:id AND user_id=:user_id",
            fields,
        )


def delete_job(job_id: str, user_id: int) -> bool:
    job = get_job(job_id, user_id)
    if not job:
        return False
    with get_db() as conn:
        conn.execute("DELETE FROM bench_jobs WHERE id=? AND user_id=?", (job_id, user_id))
    # 清理整个任务目录
    result_path = job.get("result_path") or ""
    if result_path:
        folder = Path(result_path).parent
        try:
            if folder.exists() and _BENCH_ROOT in folder.parents:
                shutil.rmtree(folder, ignore_errors=True)
        except OSError:
            pass
    return True


# ---------- 取消标记（内存态） ----------
_cancelled: set[str] = set()


def request_cancel(job_id: str) -> None:
    _cancelled.add(job_id)


def is_cancelled(job_id: str) -> bool:
    return job_id in _cancelled


def clear_cancel(job_id: str) -> None:
    _cancelled.discard(job_id)


__all__ = [
    "MAX_FILE_BYTES",
    "timestamp",
    "new_upload_id",
    "new_job_id",
    "staging_path",
    "save_staging",
    "read_staging",
    "delete_staging",
    "create_job_folder",
    "import_staging_to_params",
    "insert_job",
    "list_jobs",
    "get_job",
    "update_job",
    "delete_job",
    "request_cancel",
    "is_cancelled",
    "clear_cancel",
]
