"""批量测试异步执行器。

- 用 asyncio.Semaphore 控制并发（语义对应用户说的"线程数"）；
- 每行数据用 CSV 列值替换模板里的 {{列名}}，内置占位符（{{$uuid}} 等）逐行重新生成；
- 非流式：普通请求，记总耗时 + 响应体；
- 流式（OpenAI 兼容 SSE）：逐帧解析 data: {...}，记首帧耗时(TTFT)，累加 delta 为完整文本；
- 结果逐行写入 CSV（UTF-8 BOM，Excel 直接打开不乱码），并回写任务进度。
"""
from __future__ import annotations

import asyncio
import csv
import io
import json
import random
import re
import time
import uuid
from pathlib import Path

import httpx

from backend.app.schemas.bench import BenchRequestTemplate
from backend.app.services import bench_store
from backend.app.services.net_util import rewrite_loopback

_VAR_RE = re.compile(r"\{\{\s*([A-Za-z0-9_.$-]+)\s*\}\}")
_TIMEOUT = httpx.Timeout(connect=10.0, read=120.0, write=30.0, pool=10.0)


def _builtin_var(name: str) -> str | None:
    """内置占位符逐行生成值。"""
    now = time.time()
    table = {
        "$uuid": str(uuid.uuid4()),
        "$timestamp": str(int(now)),
        "$timestampMs": str(int(now * 1000)),
        "$datetime": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now)),
        "$date": time.strftime("%Y-%m-%d", time.localtime(now)),
        "$time": time.strftime("%H:%M:%S", time.localtime(now)),
        "$randomInt": str(random.randint(0, 100000)),
        "$randomString": uuid.uuid4().hex[:12],
    }
    return table.get(name)


def render(text: str, row: dict[str, str]) -> str:
    """把文本里的 {{var}} 替换为 行列值 > 内置占位符；未匹配的原样保留。最多迭代 5 轮。"""
    if not text:
        return text

    def lookup(name: str) -> str | None:
        if name in row and row[name] is not None:
            return str(row[name])
        return _builtin_var(name)

    out = text
    for _ in range(5):
        changed = False

        def repl(m: re.Match) -> str:
            nonlocal changed
            val = lookup(m.group(1))
            if val is not None:
                changed = True
                return val
            return m.group(0)

        out = _VAR_RE.sub(repl, out)
        if not changed:
            break
    return out


def _headers_dict(headers: list[dict], row: dict[str, str]) -> dict[str, str]:
    out = {}
    for h in headers:
        if h.get("enabled", True) and h.get("key"):
            out[h["key"]] = render(str(h.get("value", "")), row)
    return out


def _params_dict(params: list[dict], row: dict[str, str]) -> dict[str, str]:
    out = {}
    for p in params:
        if p.get("enabled", True) and p.get("key"):
            out[p["key"]] = render(str(p.get("value", "")), row)
    return out


def _parse_openai_stream_line(line: str) -> str:
    """从一行 SSE data 里取出文本 delta；非文本帧返回 ''。"""
    line = line.strip()
    if not line or not line.startswith("data:"):
        return ""
    payload = line[5:].strip()
    if payload == "[DONE]":
        return ""
    try:
        obj = json.loads(payload)
    except json.JSONDecodeError:
        return ""
    choices = obj.get("choices") or []
    if not choices:
        return ""
    delta = choices[0].get("delta") or {}
    return str(delta.get("content") or "")


# ---------- 自定义结果列：取值路径解析 ----------

_TOKEN_RE = re.compile(r"[^.\[\]]+")
_ROOT_PREFIXES = ("response", "body", "result")


def _split_path(path: str) -> list[str]:
    """把 `response.data[0].name` 拆成 ['data','0','name']。

    支持 `$` / `$.` / `response.` / `body.` / `result.` 前缀，点号与方括号可混用。
    """
    p = (path or "").strip()
    if p.startswith("$"):
        p = p[1:]
    low = p.lower()
    for pre in _ROOT_PREFIXES:
        if low == pre:
            return []
        if low.startswith(pre + ".") or low.startswith(pre + "["):
            p = p[len(pre):]
            break
    p = p.lstrip(".")
    return [t.strip().strip("'\"") for t in _TOKEN_RE.findall(p) if t.strip()]


def _to_text(value) -> str:
    """把取到的值转成 CSV 单元格文本（容器类型转紧凑 JSON）。"""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    except (TypeError, ValueError):
        return str(value)


def extract_value(obj, path: str) -> str:
    """按点号/下标路径从已解析的 JSON 对象里取值；取不到返回 ''。"""
    if obj is None:
        return ""
    tokens = _split_path(path)
    if not tokens:
        return _to_text(obj)
    cur = obj
    for tok in tokens:
        if isinstance(cur, dict):
            if tok not in cur:
                return ""
            cur = cur[tok]
        elif isinstance(cur, list):
            try:
                idx = int(tok)
            except (TypeError, ValueError):
                return ""
            if idx < -len(cur) or idx >= len(cur):
                return ""
            cur = cur[idx]
        else:
            return ""
        if cur is None:
            return ""
    return _to_text(cur)


def _load_json(text: str):
    """宽松解析响应体为 JSON 对象；非 JSON 返回 None。"""
    if not text:
        return None
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError, ValueError):
        return None


def _sse_payload(line: str):
    """从一行 SSE 里取出 data 的 JSON 对象；非 JSON 帧返回 None。"""
    line = (line or "").strip()
    if not line:
        return None
    payload = line[5:].strip() if line.startswith("data:") else line
    if not payload or payload == "[DONE]":
        return None
    if payload[:1] not in ("{", "["):
        return None
    try:
        return json.loads(payload)
    except (json.JSONDecodeError, ValueError):
        return None


async def _run_one(
    client: httpx.AsyncClient,
    tpl: BenchRequestTemplate,
    row: dict[str, str],
    streaming: bool,
    columns: list[tuple[str, str]] | None = None,
    loopback_target: str = "",
) -> dict:
    """跑单行数据，返回一条结果字典。瞬时连接错误自动重试 1 次。

    columns 为 [(表头, 取值路径)]：非流式从完整响应体提取；流式逐帧提取，
    某列一旦取到非空值即定稿，后续帧不再覆盖。
    """
    columns = columns or []
    # 逐行渲染后才知道 URL 的真实 host，这里有最后一次机会把回环地址换成可达地址
    url = rewrite_loopback(render(tpl.url, row), loopback_target)
    headers = _headers_dict(tpl.headers, row)
    params = _params_dict(tpl.params, row)
    body = render(tpl.body, row) if tpl.body else None
    content = None
    if tpl.body_type == "json":
        headers.setdefault("Content-Type", "application/json")
        content = body
    elif tpl.body_type == "raw":
        content = body

    result = {
        "status": 0,
        "ok": False,
        "total_ms": 0,
        "ttft_ms": "",
        "size_bytes": 0,
        "error": "",
        "text": "",
        "retried": False,
        "extracted": {title: "" for title, _ in columns},
    }
    start = time.perf_counter()

    # 值得重试的传输层错误（被测接口在并发下短时掐连接）
    transient = (
        httpx.ConnectError,
        httpx.ConnectTimeout,
        httpx.ReadError,
        httpx.RemoteProtocolError,
        httpx.PoolTimeout,
    )

    async def attempt() -> None:
        """单次尝试；网络异常直接抛出，HTTP 状态码不抛。"""
        ttft = None
        # 重试时重置已提取的值，避免把上一次的半截结果留下来
        found = {title: "" for title, _ in columns}
        result["extracted"] = found
        if streaming:
            chunks: list[str] = []
            size = 0
            async with client.stream(
                tpl.method, url, headers=headers, params=params, content=content
            ) as resp:
                result["status"] = resp.status_code
                async for line in resp.aiter_lines():
                    if ttft is None:
                        ttft = (time.perf_counter() - start) * 1000
                    delta = _parse_openai_stream_line(line)
                    if delta:
                        chunks.append(delta)
                        size += len(delta.encode("utf-8"))
                    # 自定义列：帧数据为空则跳过；已有值的列不再覆盖
                    if columns and any(not v for v in found.values()):
                        frame = _sse_payload(line)
                        if frame is None:
                            continue
                        for title, path in columns:
                            if found[title]:
                                continue
                            val = extract_value(frame, path)
                            if val:
                                found[title] = val
            result["text"] = "".join(chunks)
            result["ttft_ms"] = int(ttft) if ttft is not None else ""
            result["size_bytes"] = size
        else:
            resp = await client.request(
                tpl.method, url, headers=headers, params=params, content=content
            )
            result["status"] = resp.status_code
            raw = resp.content
            result["size_bytes"] = len(raw)
            result["text"] = raw.decode("utf-8", errors="replace")
            result["ttft_ms"] = ""
            if columns:
                obj = _load_json(result["text"])
                if obj is not None:
                    for title, path in columns:
                        found[title] = extract_value(obj, path)

    last_err: Exception | None = None
    for attempt_idx in range(2):  # 首次 + 最多 1 次重试
        try:
            await attempt()
            last_err = None
            break
        except httpx.ReadTimeout:
            last_err = RuntimeError("超时")
            break  # 读超时重试意义不大（请求可能已在处理）
        except transient as exc:
            last_err = exc
            result["retried"] = True
            await asyncio.sleep(0.3)  # 短暂退避
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            break

    if last_err is not None:
        result["error"] = str(last_err)[:300]
    else:
        result["ok"] = 200 <= result["status"] < 400
    result["total_ms"] = int((time.perf_counter() - start) * 1000)
    return result


def _read_csv_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    """读取上传的 CSV，返回 (列名, 行列表)。兼容 utf-8-sig BOM。"""
    raw = path.read_bytes()
    text = raw.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    fields = reader.fieldnames or []
    rows: list[dict[str, str]] = []
    for r in reader:
        rows.append({k: ("" if v is None else str(v)) for k, v in r.items()})
    return list(fields), rows


def build_result_header(
    fields: list[str],
    streaming: bool,
    custom_titles: list[str],
    input_columns: list[str] | None = None,
) -> tuple[list[str], list[str]]:
    """结果 CSV 表头：选中的测试集输入列 → 固定指标列 → 自定义列。

    input_columns 为空/None 时不写输入列；只保留测试集里真实存在的列，顺序按测试集原顺序。
    返回 (表头, 实际写入的输入列原名)。
    """
    text_col = "content" if streaming else "响应原文"
    metric_header = [
        "序号", "状态码", "是否成功", "总耗时ms", "首帧耗时ms",
        "响应字节数", "是否重试", "错误信息", text_col,
    ]
    wanted = {str(c).strip() for c in (input_columns or []) if str(c).strip()}
    picked = [f for f in fields if f in wanted]

    taken = set(metric_header)
    # 自定义列名与指标列重名时加「（提取）」后缀，保证按列名取值不串
    safe_customs: list[str] = []
    for t in custom_titles:
        name = t
        if name in taken:
            name = f"{name}（提取）"
        taken.add(name)
        safe_customs.append(name)
    input_headers: list[str] = []
    for f in picked:
        name = (f or "列").strip() or "列"
        if name in taken:
            name = f"{name}（输入）"
        taken.add(name)
        input_headers.append(name)
    return input_headers + metric_header + safe_customs, picked


async def run_job(
    job: dict,
    tpl: BenchRequestTemplate,
    env_vars: dict | None = None,
    columns: list | None = None,
    input_columns: list[str] | None = None,
    loopback_target: str = "",
) -> None:
    """后台协程：跑完整个任务并回写状态/统计/CSV。job 为 DB 行字典。

    columns 为自定义结果列（BenchColumn 或 {title, path}），会在固定指标列之后追加；
    input_columns 为要一并写进结果 CSV 的测试集输入列（只写用户勾选的那些）。
    """
    env_vars = env_vars or {}
    sorted_columns: list[tuple[str, str]] = []
    for c in columns or []:
        title = str(getattr(c, "title", None) or (c.get("title") if isinstance(c, dict) else "") or "").strip()
        path = str(getattr(c, "path", None) or (c.get("path") if isinstance(c, dict) else "") or "").strip()
        if title and path:
            sorted_columns.append((title, path))
    user_id = job["user_id"]
    job_id = job["id"]
    upload = Path(job["params_path"])
    result = Path(job["result_path"])

    try:
        fields, rows = _read_csv_rows(upload)
    except Exception as exc:  # noqa: BLE001
        bench_store.update_job(job_id, user_id, status="failed", error=f"读取数据文件失败：{exc}")
        return

    total = len(rows)
    bench_store.update_job(job_id, user_id, total=total, columns_json=json.dumps(fields, ensure_ascii=False))
    if total == 0:
        bench_store.update_job(job_id, user_id, status="failed", error="数据文件没有有效数据行")
        return

    sem = asyncio.Semaphore(job["concurrency"])
    done = 0
    success = 0
    fail = 0
    latencies: list[int] = []
    ttfts: list[int] = []

    # CSV 写出（带 BOM）：测试集输入列 → 固定指标列 → 自定义列，便于直接对照「输入 → 输出」
    out_f = open(result, "w", encoding="utf-8-sig", newline="")
    writer = csv.writer(out_f)
    streaming = bool(job["streaming"])
    custom_titles = [title for title, _ in sorted_columns]
    header, picked_inputs = build_result_header(fields, streaming, custom_titles, input_columns)
    writer.writerow(header)

    async def bounded(idx_row: tuple[int, dict]) -> None:
        nonlocal done, success, fail
        idx, row = idx_row
        # 必须在拿到并发槽位之后再检查取消，否则 gather 启动时一次性全部穿过检查、排队到信号量上，
        # 之后取消标记置位也不会被这些协程再次看到。
        async with sem:
            if bench_store.is_cancelled(job_id):
                return
            merged = {**env_vars, **row}
            r = await _run_one(client, tpl, merged, streaming, sorted_columns, loopback_target)
        writer.writerow(
            [row.get(f, "") for f in picked_inputs]
            + [
                idx + 1, r["status"], "成功" if r["ok"] else "失败",
                r["total_ms"], r["ttft_ms"], r["size_bytes"],
                "是" if r.get("retried") else "",
                r["error"], r["text"],
            ]
            + [r["extracted"].get(title, "") for title, _ in sorted_columns]
        )
        out_f.flush()
        done += 1
        if r["ok"]:
            success += 1
        else:
            fail += 1
        latencies.append(r["total_ms"])
        if isinstance(r["ttft_ms"], int):
            ttfts.append(r["ttft_ms"])
        # 每 10 行回写一次进度，让前端轮询能看到进展
        if done % 10 == 0:
            bench_store.update_job(
                job_id, user_id, done=done, success=success, fail=fail,
            )

    # 连接池上限 = 并发数，避免池等待成为瓶颈；keepalive 关闭以复用以防被对端掐断的旧连接
    limits = httpx.Limits(
        max_connections=max(job["concurrency"], 1),
        max_keepalive_connections=0,
    )
    try:
        async with httpx.AsyncClient(
            timeout=_TIMEOUT, follow_redirects=True, limits=limits
        ) as client:
            await asyncio.gather(*[bounded(enumerate_row) for enumerate_row in enumerate(rows)])
    finally:
        out_f.close()

    latencies.sort()
    avg = sum(latencies) / len(latencies) if latencies else 0
    p95 = latencies[int(len(latencies) * 0.95) - 1] if latencies else 0
    ttft_avg = sum(ttfts) / len(ttfts) if ttfts else 0

    if bench_store.is_cancelled(job_id):
        bench_store.clear_cancel(job_id)
        bench_store.update_job(
            job_id, user_id,
            status="cancelled", done=done, success=success, fail=fail,
            error=f"用户已取消（完成 {done}/{total}）",
        )
        return

    bench_store.update_job(
        job_id, user_id,
        status="done", done=done, success=success, fail=fail,
        avg_ms=round(avg, 1), p95_ms=round(float(p95), 1), ttft_avg_ms=round(ttft_avg, 1),
    )

    # 生成 HTML 报告（失败不影响任务状态）
    try:
        from backend.app.services import bench_report
        html_str = bench_report.render_report(job, Path(result))
        report_path = Path(result).with_suffix(".report.html")
        report_path.write_text(html_str, encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        print(f"[bench] report generation failed: {exc}")
