"""批量/压测 API。

- POST /api/bench/upload        上传 CSV 数据文件（<=10MB），返回列名与行数预览
- POST /api/bench/run           用模板请求 + 数据文件发起批量测试（后台异步执行）
- GET  /api/bench/jobs           当前用户的任务记录列表
- GET  /api/bench/jobs/{id}/csv 下载结果 CSV
- DELETE /api/bench/jobs/{id}    删除任务记录（连同任务目录）
"""
from __future__ import annotations

import asyncio
import csv
import io

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse

from backend.app.api.auth import current_user
from backend.app.schemas.bench import BenchRequestTemplate, BenchRunBody
from backend.app.services import bench_store

router = APIRouter()

# 持有后台任务引用，避免被 GC 提前回收
_bg_tasks: set[asyncio.Task] = set()


@router.post("/upload")
async def upload(file: UploadFile = File(...), user: dict = Depends(current_user)) -> dict:
    name = file.filename or "data.csv"
    raw = await file.read()
    if len(raw) > bench_store.MAX_FILE_BYTES:
        raise HTTPException(status_code=400, detail="文件超过 10MB 限制")
    if not raw.strip():
        raise HTTPException(status_code=400, detail="文件为空")

    upload_id = bench_store.new_upload_id()
    bench_store.save_staging(upload_id, raw)

    # 预览：解析列名与行数
    text = raw.decode("utf-8-sig", errors="replace")
    try:
        reader = csv.DictReader(io.StringIO(text))
        columns = reader.fieldnames or []
        row_count = sum(1 for _ in reader)
    except Exception as exc:  # noqa: BLE001
        bench_store.delete_staging(upload_id)
        raise HTTPException(status_code=400, detail=f"CSV 解析失败：{exc}")
    if not columns:
        bench_store.delete_staging(upload_id)
        raise HTTPException(status_code=400, detail="CSV 缺少表头（第一行应为占位符名）")

    return {"upload_id": upload_id, "filename": name, "columns": columns, "rows": row_count}


@router.post("/run")
async def run(body: BenchRunBody, user: dict = Depends(current_user)) -> dict:
    from pathlib import Path

    # 校验上传文件存在
    staging = bench_store.staging_path(body.upload_id)
    if not staging.exists():
        raise HTTPException(status_code=404, detail="数据文件不存在，请重新上传")

    job_id = bench_store.new_job_id()
    ts = bench_store.timestamp()
    # 建立 <接口名>_<时间>/ 目录，参数文件移动进去
    _folder, params_path, result_path = bench_store.create_job_folder(body.name, ts)
    bench_store.import_staging_to_params(body.upload_id, params_path)

    fields = {
        "id": job_id,
        "user_id": user["id"],
        "name": body.name or "批量测试",
        "status": "running",
        "concurrency": body.concurrency,
        "streaming": 1 if body.streaming else 0,
        "params_path": str(params_path),
        "result_path": str(result_path),
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
async def jobs(user: dict = Depends(current_user)) -> list[dict]:
    return bench_store.list_jobs(user["id"])


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
