"""压测报告生成：读取结果 CSV，输出一个自包含 HTML（内联 CSS + SVG，无外部依赖）。"""
from __future__ import annotations

import csv
import html
import io
from collections import Counter
from pathlib import Path


def _pct(sorted_vals: list[float], q: float) -> float:
    if not sorted_vals:
        return 0
    idx = min(len(sorted_vals) - 1, int(len(sorted_vals) * q))
    return sorted_vals[idx]


def _histogram(latencies: list[float], buckets: int = 10) -> list[tuple[str, int]]:
    if not latencies:
        return []
    lo, hi = min(latencies), max(latencies)
    if hi == lo:
        return [(f"{hi:.0f}ms", len(latencies))]
    step = (hi - lo) / buckets
    counts = [0] * buckets
    for v in latencies:
        b = min(buckets - 1, int((v - lo) / step))
        counts[b] += 1
    out = []
    for i, c in enumerate(counts):
        lo_b = lo + i * step
        hi_b = lo + (i + 1) * step
        out.append((f"{lo_b:.0f}–{hi_b:.0f}ms", c))
    return out


def render_report(job: dict, result_csv: Path) -> str:
    """根据 job 记录和结果 CSV 生成完整 HTML 字符串。"""
    latencies: list[float] = []
    ttfts: list[float] = []
    status_counter: Counter[str] = Counter()
    success = 0
    fail = 0
    with open(result_csv, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                latencies.append(float(row.get("总耗时ms") or 0))
            except ValueError:
                pass
            ttft = row.get("首帧耗时ms") or ""
            if ttft not in ("", "-"):
                try:
                    ttfts.append(float(ttft))
                except ValueError:
                    pass
            status_counter[str(row.get("状态码") or "-")] += 1
            if (row.get("是否成功") or "") == "成功":
                success += 1
            else:
                fail += 1

    latencies.sort()
    total = len(latencies) or 1
    avg = sum(latencies) / total if latencies else 0
    p50 = _pct(latencies, 0.50)
    p90 = _pct(latencies, 0.90)
    p95 = _pct(latencies, 0.95)
    p99 = _pct(latencies, 0.99)
    ttft_avg = sum(ttfts) / len(ttfts) if ttfts else 0
    err_rate = fail / (success + fail) * 100 if (success + fail) else 0

    hist = _histogram(latencies)
    hist_max = max((c for _, c in hist), default=1)

    # 状态码分布
    status_rows = "".join(
        f"<tr><td>{html.escape(s)}</td><td>{c}</td>"
        f"<td class='num'>{c / total * 100:.1f}%</td></tr>"
        for s, c in sorted(status_counter.items(), key=lambda x: -x[1])
    )

    # 直方图条
    hist_bars = "".join(
        f"<div class='bar-row'><span class='bar-label'>{label}</span>"
        f"<span class='bar-track'><span class='bar-fill' style='width:{c / hist_max * 100:.1f}%'></span></span>"
        f"<span class='bar-count'>{c}</span></div>"
        for label, c in hist
    )

    name = html.escape(job.get("name") or "批量测试")
    created = html.escape(job.get("created_at") or "")
    concurrency = job.get("concurrency") or 1

    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>压测报告 · {name}</title>
<style>
  body {{ font-family: -apple-system, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
         margin: 0; padding: 32px; background: #f6f7f9; color: #1f2329; }}
  .wrap {{ max-width: 960px; margin: 0 auto; }}
  h1 {{ font-size: 22px; margin: 0 0 4px; }}
  .sub {{ color: #86909c; font-size: 13px; margin-bottom: 24px; }}
  .cards {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 24px; }}
  .card {{ background: #fff; border: 1px solid #e5e6eb; border-radius: 8px; padding: 14px 16px; }}
  .card .k {{ font-size: 12px; color: #86909c; }}
  .card .v {{ font-size: 22px; font-weight: 600; margin-top: 4px; font-variant-numeric: tabular-nums; }}
  .card .v small {{ font-size: 12px; color: #86909c; font-weight: 400; }}
  .panel {{ background: #fff; border: 1px solid #e5e6eb; border-radius: 8px; padding: 16px 20px; margin-bottom: 16px; }}
  .panel h2 {{ font-size: 14px; margin: 0 0 12px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th, td {{ text-align: left; padding: 6px 8px; border-bottom: 1px solid #f0f1f3; }}
  th.num, td.num {{ text-align: left; font-variant-numeric: tabular-nums; }}
  .bar-row {{ display: grid; grid-template-columns: 140px 1fr 40px; gap: 8px; align-items: center;
              font-size: 12px; margin: 4px 0; }}
  .bar-label {{ color: #4e5969; font-family: ui-monospace, Menlo, monospace; }}
  .bar-track {{ height: 10px; background: #f2f3f5; border-radius: 5px; overflow: hidden; }}
  .bar-fill {{ display: block; height: 100%; background: #165dff; }}
  .bar-count {{ text-align: right; color: #4e5969; font-variant-numeric: tabular-nums; }}
  .ok {{ color: #00b42a; }} .bad {{ color: #f53f3f; }}
</style></head>
<body><div class="wrap">
  <h1>压测报告 · {name}</h1>
  <div class="sub">开始时间 {created} · 并发 {concurrency}</div>

  <div class="cards">
    <div class="card"><div class="k">总请求</div><div class="v">{total}</div></div>
    <div class="card"><div class="k">成功 / 失败</div>
      <div class="v"><span class="ok">{success}</span> / <span class="bad">{fail}</span></div></div>
    <div class="card"><div class="k">错误率</div>
      <div class="v">{err_rate:.1f}<small> %</small></div></div>
    <div class="card"><div class="k">平均耗时</div>
      <div class="v">{avg:.0f}<small> ms</small></div></div>
  </div>

  <div class="panel">
    <h2>延迟分布</h2>
    <table>
      <tr><th class="num">P50</th><th class="num">P90</th><th class="num">P95</th><th class="num">P99</th><th class="num">平均 TTFT</th></tr>
      <tr>
        <td class="num">{p50:.0f} ms</td>
        <td class="num">{p90:.0f} ms</td>
        <td class="num">{p95:.0f} ms</td>
        <td class="num">{p99:.0f} ms</td>
        <td class="num">{ttft_avg:.0f} ms</td>
      </tr>
    </table>
  </div>

  <div class="panel">
    <h2>耗时直方图（ms）</h2>
    {hist_bars or "<div class='sub'>无数据</div>"}
  </div>

  <div class="panel">
    <h2>状态码分布</h2>
    <table>
      <tr><th>状态码</th><th>次数</th><th>占比</th></tr>
      {status_rows}
    </table>
  </div>
</div></body></html>
"""
