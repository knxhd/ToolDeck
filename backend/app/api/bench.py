"""批量/压测 API。

- POST /api/bench/datasets          创建测试集（上传 CSV 并命名，可反复复用）
- GET  /api/bench/datasets          测试集列表
- PUT  /api/bench/datasets/{id}     重命名测试集
- GET  /api/bench/datasets/{id}/csv 下载测试集原始 CSV
- DELETE /api/bench/datasets/{id}   删除测试集
- POST /api/bench/upload            一次性上传 CSV（不落测试集，兼容旧流程）
- POST /api/bench/run               用模板请求 + 测试集/数据文件发起批量测试
- GET  /api/bench/jobs              当前用户的任务记录列表（可按接口过滤）
- GET  /api/bench/jobs/{id}/csv     下载结果 CSV
- DELETE /api/bench/jobs/{id}       删除任务记录（连同任务目录）
"""
from __future__ import annotations

import asyncio
import csv
import io
import json

from fastapi import APIRouter, Body, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse

from backend.app.api.auth import current_user
from backend.app.schemas.bench import BenchRequestTemplate, BenchRunBody
from backend.app.services import bench_store

router = APIRouter()

# 持有后台任务引用，避免被 GC 提前回收
_bg_tasks: set[asyncio.Task] = set()


def _parse_csv(raw: bytes) -> tuple[list[str], int]:
    """解析 CSV 字节流，返回 (表头列名, 数据行数)。"""
    text = raw.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    columns = reader.fieldnames or []
    row_count = sum(1 for _ in reader)
    if not columns:
        raise ValueError("CSV 缺少表头（第一行应为占位符名）")
    return columns, row_count


async def _read_csv_upload(file: UploadFile) -> bytes:
    raw = await file.read()
    if len(raw) > bench_store.MAX_FILE_BYTES:
        raise HTTPException(status_code=400, detail="文件超过 10MB 限制")
    if not raw.strip():
        raise HTTPException(status_code=400, detail="文件为空")
    return raw


@router.post("/datasets")
async def create_dataset(
    file: UploadFile = File(...),
    name: str = Form(""),
    user: dict = Depends(current_user),
) -> dict:
    """上传一份 CSV 并保存为命名测试集。"""
    raw = await _read_csv_upload(file)
    try:
        columns, row_count = _parse_csv(raw)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"CSV 解析失败：{exc}")

    dataset_id = bench_store.new_dataset_id()
    dataset_name = (name or file.filename or "测试集").strip()[:100] or "测试集"
    path = bench_store.save_dataset_file(dataset_id, raw)
    bench_store.insert_dataset({
        "id": dataset_id,
        "user_id": user["id"],
        "name": dataset_name,
        "columns_json": json.dumps(columns, ensure_ascii=False),
        "rows": row_count,
        "path": str(path),
    })
    return {
        "id": dataset_id,
        "name": dataset_name,
        "columns": columns,
        "rows": row_count,
    }


@router.get("/datasets")
async def datasets(user: dict = Depends(current_user)) -> list[dict]:
    return bench_store.list_datasets(user["id"])


@router.put("/datasets/{dataset_id}")
async def rename_dataset(
    dataset_id: str,
    payload: dict = Body(...),
    user: dict = Depends(current_user),
) -> dict:
    name = str(payload.get("name") or "").strip()[:100]
    if not name:
        raise HTTPException(status_code=400, detail="名称不能为空")
    if not bench_store.rename_dataset(dataset_id, user["id"], name):
        raise HTTPException(status_code=404, detail="测试集不存在")
    return {"id": dataset_id, "name": name}


@router.get("/datasets/{dataset_id}/csv")
async def download_dataset(dataset_id: str, user: dict = Depends(current_user)) -> FileResponse:
    ds = bench_store.get_dataset(dataset_id, user["id"])
    if not ds:
        raise HTTPException(status_code=404, detail="测试集不存在")
    p = bench_store.dataset_path(dataset_id)
    if not p.exists():
        raise HTTPException(status_code=404, detail="测试集文件不存在")
    return FileResponse(p, media_type="text/csv", filename=f"{ds['name']}.csv")


@router.get("/datasets/{dataset_id}/preview")
async def preview_dataset(
    dataset_id: str,
    limit: int = 50,
    user: dict = Depends(current_user),
) -> dict:
    """预览测试集内容：返回表头与前 limit 行数据（总行数单独给出）。"""
    ds = bench_store.get_dataset(dataset_id, user["id"])
    if not ds:
        raise HTTPException(status_code=404, detail="测试集不存在")
    p = bench_store.dataset_path(dataset_id)
    if not p.exists():
        raise HTTPException(status_code=404, detail="测试集文件不存在")
    limit = max(1, min(int(limit), 500))
    text = p.read_bytes().decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    columns = reader.fieldnames or []
    rows: list[dict] = []
    for i, r in enumerate(reader):
        if i >= limit:
            break
        rows.append({k: ("" if v is None else str(v)) for k, v in r.items()})
    return {
        "id": dataset_id,
        "name": ds["name"],
        "columns": columns,
        "rows": ds["rows"],
        "preview": rows,
        "limit": limit,
    }


@router.delete("/datasets/{dataset_id}")
async def remove_dataset(dataset_id: str, user: dict = Depends(current_user)) -> dict:
    if not bench_store.delete_dataset(dataset_id, user["id"]):
        raise HTTPException(status_code=404, detail="测试集不存在")
    return {"deleted": True}


@router.post("/upload")
async def upload(file: UploadFile = File(...), user: dict = Depends(current_user)) -> dict:
    """一次性上传（不保存为测试集），保留给旧流程/接口调用使用。"""
    name = file.filename or "data.csv"
    raw = await _read_csv_upload(file)

    upload_id = bench_store.new_upload_id()
    bench_store.save_staging(upload_id, raw)

    try:
        columns, row_count = _parse_csv(raw)
    except Exception as exc:  # noqa: BLE001
        bench_store.delete_staging(upload_id)
        raise HTTPException(status_code=400, detail=f"CSV 解析失败：{exc}")

    return {"upload_id": upload_id, "filename": name, "columns": columns, "rows": row_count}


@router.post("/run")
async def run(body: BenchRunBody, user: dict = Depends(current_user)) -> dict:
    dataset_id = body.dataset_id.strip()
    upload_id = body.upload_id.strip()

    # 校验数据来源：优先测试集，其次一次性上传
    if dataset_id:
        if not bench_store.get_dataset(dataset_id, user["id"]):
            raise HTTPException(status_code=404, detail="测试集不存在")
    elif not bench_store.staging_path(upload_id).exists():
        raise HTTPException(status_code=404, detail="数据文件不存在，请重新上传")

    job_id = bench_store.new_job_id()
    ts = bench_store.timestamp()
    # 建立 <接口名>_<时间>/ 目录，测试集复制进去（测试集本身保留）
    _folder, params_path, result_path = bench_store.create_job_folder(body.name, ts)
    if dataset_id:
        try:
            bench_store.copy_dataset_to_params(dataset_id, params_path)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="测试集文件不存在")
    else:
        bench_store.import_staging_to_params(upload_id, params_path)

    fields = {
        "id": job_id,
        "user_id": user["id"],
        "name": body.name or "批量测试",
        "status": "running",
        "concurrency": body.concurrency,
        "streaming": 1 if body.streaming else 0,
        "params_path": str(params_path),
        "result_path": str(result_path),
        "scope_key": body.scope_key.strip()[:200],
    }
    bench_store.insert_job(fields)

    job_row = bench_store.get_job(job_id, user["id"])
    tpl = BenchRequestTemplate(**body.request.model_dump())
    columns = [c.model_dump() for c in body.columns]
    task = asyncio.create_task(bench_store_run(job_row, tpl, body.env_vars, columns))
    _bg_tasks.add(task)
    task.add_done_callback(_bg_tasks.discard)

    return {"job_id": job_id, "status": "running", "columns": [c["title"] for c in columns]}


async def bench_store_run(
    job_row: dict,
    tpl: BenchRequestTemplate,
    env_vars: dict | None = None,
    columns: list | None = None,
) -> None:
    """延迟导入执行器，避免循环依赖。"""
    from backend.app.services.bench_runner import run_job

    await run_job(job_row, tpl, env_vars, columns)


@router.get("/jobs")
async def jobs(
    scope_key: str = "",
    user: dict = Depends(current_user),
) -> list[dict]:
    """任务记录；带 scope_key 时只返回该接口下的任务。"""
    return bench_store.list_jobs(user["id"], scope_key.strip() or None)


@router.get("/jobs/{job_id}/csv")
async def download_csv(job_id: str, user: dict = Depends(current_user)) -> FileResponse:
    job = bench_store.get_job(job_id, user["id"])
    if not job:
        raise HTTPException(status_code=404, detail="任务不存在")
    result = job.get("result_path") or ""
    if not result:
        raise HTTPException(status_code=404, detail="结果文件路径未配置")
    from pathlib import Path

    p = Path(result)
    if not p.exists():
        raise HTTPException(status_code=404, detail="结果文件尚未生成")
    return FileResponse(
        p,
        media_type="text/csv",
        filename=f"benchmark-result-{job['name']}-{job_id}.csv",
    )


@router.get("/jobs/{job_id}/params")
async def download_params(job_id: str, user: dict = Depends(current_user)) -> FileResponse:
    job = bench_store.get_job(job_id, user["id"])
    if not job:
        raise HTTPException(status_code=404, detail="任务不存在")
    params = job.get("params_path") or ""
    if not params:
        raise HTTPException(status_code=404, detail="参数文件路径未配置")
    from pathlib import Path

    p = Path(params)
    if not p.exists():
        raise HTTPException(status_code=404, detail="参数文件不存在")
    return FileResponse(
        p,
        media_type="text/csv",
        filename=f"benchmark-params-{job['name']}-{job_id}.csv",
    )


@router.get("/jobs/{job_id}/report")
async def download_report(job_id: str, user: dict = Depends(current_user)) -> FileResponse:
    job = bench_store.get_job(job_id, user["id"])
    if not job:
        raise HTTPException(status_code=404, detail="任务不存在")
    result = job.get("result_path") or ""
    if not result:
        raise HTTPException(status_code=404, detail="结果文件路径未配置")
    from pathlib import Path

    p = Path(result).with_suffix(".report.html")
    if not p.exists():
        # 旧任务没有预生成报告，现场生成一份
        try:
            from backend.app.services import bench_report
            html_str = bench_report.render_report(job, Path(result))
            p.write_text(html_str, encoding="utf-8")
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=404, detail=f"报告生成失败：{exc}")
    return FileResponse(
        p,
        media_type="text/html",
        filename=f"benchmark-report-{job['name']}-{job_id}.html",
    )


@router.delete("/jobs/{job_id}")
async def remove_job(job_id: str, user: dict = Depends(current_user)) -> dict:
    ok = bench_store.delete_job(job_id, user["id"])
    if not ok:
        raise HTTPException(status_code=404, detail="任务不存在")
    return {"deleted": True}


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(job_id: str, user: dict = Depends(current_user)) -> dict:
    job = bench_store.get_job(job_id, user["id"])
    if not job:
        raise HTTPException(status_code=404, detail="任务不存在")
    if job["status"] == "running":
        bench_store.request_cancel(job_id)
    return {"cancelled": True}
