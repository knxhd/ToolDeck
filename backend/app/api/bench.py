"""批量/压测 API。

- POST /api/bench/datasets          创建测试集（上传 CSV 并命名，可反复复用）
- GET  /api/bench/datasets          测试集列表
- PUT  /api/bench/datasets/{id}     重命名测试集
- GET  /api/bench/datasets/{id}/csv 下载测试集原始 CSV
- DELETE /api/bench/datasets/{id}   删除测试集
- POST /api/bench/upload            一次性上传 CSV（不落测试集，兼容旧流程）
- POST /api/bench/run               用模板请求 + 测试集/数据文件发起批量测试
- GET  /api/bench/jobs              当前用户的任务记录列表（可按接口过滤）
- GET  /api/bench/jobs/{id}/csv     下载结果 CSV（with_annotations=1 时追加标注列）
- GET  /api/bench/jobs/{id}/rows    按页读取结果行（结果查看页用）
- GET  /api/bench/jobs/{id}/annotations   读取自定义标注列与单元格
- PUT  /api/bench/jobs/{id}/annotations   保存标注（整体覆盖）
- GET  /api/bench/jobs/{id}/view          读取结果页视图设置
- PUT  /api/bench/jobs/{id}/view          保存结果页视图设置（整体覆盖）
- DELETE /api/bench/jobs/{id}       删除任务记录（连同任务目录）
"""
from __future__ import annotations

import asyncio
import csv
from datetime import datetime
import io
import json

from fastapi import APIRouter, Body, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse

from backend.app.api.auth import current_user
from backend.app.schemas.bench import BenchRequestTemplate, BenchRunBody
from backend.app.services import bench_store

router = APIRouter()


def _job_stamp(job: dict) -> str:
    """任务时间戳 yyyy-mm-dd-hhmmss（取任务创建时间，取不到就用当前时间）。"""
    raw = str(job.get("created_at") or "")
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(raw[:19], fmt).strftime("%Y-%m-%d-%H%M%S")
        except ValueError:
            continue
    return datetime.now().strftime("%Y-%m-%d-%H%M%S")


def _job_base_name(job: dict, kind: str = "测试结果") -> str:
    """下载文件名前缀：测试集名_<kind>_yyyy-mm-dd-hhmmss。"""
    name = str(job.get("dataset_name") or job.get("name") or "批量测试")
    for ch in '\\/:*?"<>|':
        name = name.replace(ch, "_")
    return f"{name}_{kind}_{_job_stamp(job)}"

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


# ---------- 结果查看 / 标注 ----------

def _read_result_slice(path, offset: int, limit: int) -> tuple[list[str], list[list[str]], int]:
    """流式读取结果 CSV，只保留 [offset, offset+limit) 的行，返回 (表头, 行, 总行数)。"""
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        header = next(reader, [])
        rows: list[list[str]] = []
        i = 0
        for r in reader:
            if i >= offset and len(rows) < limit:
                rows.append(r)
            i += 1
    return header, rows, i


def _assign_annotation_header(base: list[str], ann_cols: list[dict]) -> list[str]:
    """把标注列名追加到结果表头；与已有列重名时加「（标注）」后缀并保证唯一。"""
    taken = set(base)
    names: list[str] = []
    for c in ann_cols:
        name = str(c.get("name") or "").strip() or "标注"
        if name in taken:
            name = f"{name}（标注）"
        base_name, n = name, 2
        while name in taken:
            name = f"{base_name}{n}"
            n += 1
        taken.add(name)
        names.append(name)
    return names


def _write_annotated_csv(job: dict, src, user_id: int):
    """把标注列追加到结果 CSV，生成同目录下的 _.annotated.csv 并返回其路径。"""
    from pathlib import Path

    ann = bench_store.get_annotations(job["id"], user_id)
    ann_cols = [c for c in ann.get("cols", []) if isinstance(c, dict) and c.get("id")]
    cells = ann.get("cells", {})
    if not ann_cols:
        return src  # 没有标注列，直接返回原文件
    out = Path(src).with_suffix(".annotated.csv")
    with open(src, "r", encoding="utf-8-sig", newline="") as fin, \
            open(out, "w", encoding="utf-8-sig", newline="") as fout:
        reader = csv.reader(fin)
        writer = csv.writer(fout)
        header = next(reader, [])
        writer.writerow(header + _assign_annotation_header(header, ann_cols))
        for i, row in enumerate(reader, start=1):
            row_cells = cells.get(str(i)) or {}
            writer.writerow(row + [str(row_cells.get(c["id"], "") or "") for c in ann_cols])
    return out


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
    ds_row: dict | None = None
    if dataset_id:
        ds_row = bench_store.get_dataset(dataset_id, user["id"])
        if not ds_row:
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
    # 记录数据来源快照：任务卡上可显示用的是哪个测试集、以及之后测试集是否被改过
    if ds_row:
        fields["dataset_id"] = dataset_id
        fields["dataset_name"] = str(ds_row.get("name") or "")[:100]
        # 用实际复制的快照文件算哈希，代表这次真正跑的数据版本
        fields["dataset_hash"] = bench_store.file_hash(params_path)
    bench_store.insert_job(fields)

    job_row = bench_store.get_job(job_id, user["id"])
    tpl = BenchRequestTemplate(**body.request.model_dump())
    columns = [c.model_dump() for c in body.columns]
    # 只把测试集里真实存在的列名透传下去（脏名字直接忽略）
    input_columns = [str(c).strip() for c in body.input_columns if str(c).strip()][:50]
    task = asyncio.create_task(
        bench_store_run(job_row, tpl, body.env_vars, columns, input_columns)
    )
    _bg_tasks.add(task)
    task.add_done_callback(_bg_tasks.discard)

    return {
        "job_id": job_id,
        "status": "running",
        "columns": [c["title"] for c in columns],
        "input_columns": input_columns,
    }


async def bench_store_run(
    job_row: dict,
    tpl: BenchRequestTemplate,
    env_vars: dict | None = None,
    columns: list | None = None,
    input_columns: list[str] | None = None,
) -> None:
    """延迟导入执行器，避免循环依赖。"""
    from backend.app.services.bench_runner import run_job

    await run_job(job_row, tpl, env_vars, columns, input_columns)


@router.get("/jobs")
async def jobs(
    scope_key: str = "",
    user: dict = Depends(current_user),
) -> list[dict]:
    """任务记录；带 scope_key 时只返回该接口下的任务。"""
    return bench_store.list_jobs(user["id"], scope_key.strip() or None)


@router.get("/jobs/{job_id}/csv")
async def download_csv(
    job_id: str,
    with_annotations: int = 0,
    user: dict = Depends(current_user),
) -> FileResponse:
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
    if with_annotations:
        annotated = _write_annotated_csv(job, p, user["id"])
        return FileResponse(
            annotated,
            media_type="text/csv",
            filename=f"{_job_base_name(job, '测试结果_标注')}.csv",
        )
    return FileResponse(
        p,
        media_type="text/csv",
        filename=f"{_job_base_name(job)}.csv",
    )


@router.get("/jobs/{job_id}/rows")
async def job_rows(
    job_id: str,
    offset: int = 0,
    limit: int = 100,
    user: dict = Depends(current_user),
) -> dict:
    """按页读取结果行，供结果查看页渲染（行号 = 结果 CSV 中的序号，1 起）。"""
    job = bench_store.get_job(job_id, user["id"])
    if not job:
        raise HTTPException(status_code=404, detail="任务不存在")
    result = job.get("result_path") or ""
    from pathlib import Path

    p = Path(result)
    if not result or not p.exists():
        raise HTTPException(status_code=404, detail="结果文件尚未生成")
    offset = max(0, offset)
    limit = max(1, min(limit, 500))
    header, rows, total = _read_result_slice(p, offset, limit)
    # 短行补空，避免前端按列索引取值出现 undefined
    rows = [r + [""] * (len(header) - len(r)) for r in rows]
    return {
        "job": {
            "id": job["id"],
            "name": job["name"],
            "status": job["status"],
            "total": job["total"],
            "done": job["done"],
            "success": job["success"],
            "fail": job["fail"],
            "concurrency": job["concurrency"],
            "streaming": job["streaming"],
            "created_at": job["created_at"],
            "stats": job["stats"],
            "dataset_name": job.get("dataset_name") or "",
        },
        "columns": header,
        "rows": rows,
        "total": total,
        "offset": offset,
        "limit": limit,
    }


@router.get("/jobs/{job_id}/annotations")
async def get_annotations(job_id: str, user: dict = Depends(current_user)) -> dict:
    job = bench_store.get_job(job_id, user["id"])
    if not job:
        raise HTTPException(status_code=404, detail="任务不存在")
    return bench_store.get_annotations(job_id, user["id"])


@router.put("/jobs/{job_id}/annotations")
async def put_annotations(
    job_id: str,
    body: dict = Body(...),
    user: dict = Depends(current_user),
) -> dict:
    """整体保存标注列与单元格（前端防抖后整份提交）。"""
    job = bench_store.get_job(job_id, user["id"])
    if not job:
        raise HTTPException(status_code=404, detail="任务不存在")
    raw_cols = body.get("cols")
    raw_cells = body.get("cells")
    if not isinstance(raw_cols, list) or not isinstance(raw_cells, dict):
        raise HTTPException(status_code=400, detail="标注数据格式不正确")
    if len(raw_cols) > 20:
        raise HTTPException(status_code=400, detail="标注列最多 20 列")
    cols = [
        {"id": str(c.get("id") or ""), "name": str(c.get("name") or "").strip()}
        for c in raw_cols
        if isinstance(c, dict) and c.get("id")
    ]
    cells: dict[str, dict[str, str]] = {}
    for row_no, values in raw_cells.items():
        if not isinstance(values, dict):
            continue
        cleaned = {str(k): str(v) for k, v in values.items() if str(v).strip()}
        if cleaned:
            cells[str(row_no)] = cleaned
    bench_store.save_annotations(job_id, user["id"], {"cols": cols, "cells": cells})
    return {"ok": True, "cols": len(cols)}


@router.get("/jobs/{job_id}/view")
async def get_view(job_id: str, user: dict = Depends(current_user)) -> dict:
    """结果页视图设置（列宽 / 隐藏列 / 换行 / 排序 / 筛选）。"""
    job = bench_store.get_job(job_id, user["id"])
    if not job:
        raise HTTPException(status_code=404, detail="任务不存在")
    return bench_store.get_view(job_id, user["id"])


@router.put("/jobs/{job_id}/view")
async def put_view(
    job_id: str,
    body: dict = Body(...),
    user: dict = Depends(current_user),
) -> dict:
    """整体保存视图设置，后端只做结构校验，字段语义由前端解释。"""
    job = bench_store.get_job(job_id, user["id"])
    if not job:
        raise HTTPException(status_code=404, detail="任务不存在")
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="视图数据格式不正确")
    payload = json.dumps(body, ensure_ascii=False)
    if len(payload) > 512 * 1024:
        raise HTTPException(status_code=400, detail="视图数据过大")
    bench_store.save_view(job_id, user["id"], body)
    return {"ok": True}


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
        filename=f"{_job_base_name(job, '测试参数')}.csv",
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
        filename=f"{_job_base_name(job, '测试报告')}.html",
    )


@router.delete("/jobs/{job_id}")
async def remove_job(job_id: str, user: dict = Depends(current_user)) -> dict:
    job = bench_store.get_job(job_id, user["id"])
    if not job:
        raise HTTPException(status_code=404, detail="任务不存在")
    # 执行中（含已点取消但尚未收尾）禁止删除：任务目录/结果文件仍在被写入
    if job.get("status") == "running":
        raise HTTPException(status_code=409, detail="任务正在执行中，请先取消并等待其结束后再删除")
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
