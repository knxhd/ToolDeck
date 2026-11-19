"""回环地址解析工具。

工具由后端发出请求，URL 里的 127.0.0.1 / localhost 永远指服务端自身，
浏览器所在的调用方机器根本连不上。这里提供两个能力：

1. rewrite_loopback：把 URL 里的回环 host 换成目标 host（保留端口、路径、query）；
2. client_ip_from_request：取这次请求的调用方 IP（兼容反向代理的 X-Forwarded-For）。

约定：
- 目标为空、或目标本身也是回环地址时，一律不改写（本地部署就是对的）；
- 只替换 host 部分，端口/路径/query 原样保留；IPv6 目标自动补方括号。
"""
from __future__ import annotations

from urllib.parse import urlsplit, urlunsplit

from starlette.requests import Request

# 视作回环的 host（含 0.0.0.0：它同样只有本机能访问）
LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1", "0.0.0.0", "127.0.1.1", "host.docker.internal"}

# 支持改写的协议前缀
_SCHEMES = ("http://", "https://", "ws://", "wss://")


def is_loopback_host(host: str) -> bool:
    """host 是否为回环/本机地址（去方括号、去空白、忽略大小写）。"""
    h = (host or "").strip().lower().strip("[]")
    return h in LOOPBACK_HOSTS


def _normalize_target(target: str) -> str:
    """目标 host 归一：去掉协议前缀与尾部斜杠，裸 IPv6 补方括号。"""
    t = (target or "").strip()
    lower = t.lower()
    for scheme in _SCHEMES:
        if lower.startswith(scheme):
            t = t[len(scheme):]
            break
    t = t.strip().strip("/")
    if t.count(":") > 1 and not t.startswith("["):
        t = f"[{t}]"
    return t


def rewrite_loopback(url: str, target: str) -> str:
    """把 url 的回环 host 换成 target；不需要改写时原样返回。

    target 可以带端口（如 10.18.217.60:48088），此时端口也一起替换。
    """
    if not url:
        return url
    tgt = _normalize_target(target)
    if not tgt:
        return url
    if not url.lower().startswith(_SCHEMES):
        return url
    try:
        parts = urlsplit(url)
    except ValueError:
        return url
    if not is_loopback_host(parts.hostname or ""):
        return url

    # 解析目标里的 host / port（支持 [::1]:8080 与 10.0.0.1:9000）
    if tgt.startswith("[") and "]:" in tgt:
        idx = tgt.index("]:")
        host, port = tgt[: idx + 1], tgt[idx + 2:]
    elif tgt.count(":") == 1:
        host, _, port = tgt.partition(":")
    else:
        host, port = tgt, ""
    if not port and parts.port:
        port = str(parts.port)
    netloc = f"{host}:{port}" if port else host

    return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))


def client_ip_from_request(request: Request) -> str:
    """调用方 IP：优先 X-Forwarded-For 首个，其次 X-Real-IP，最后直连地址。"""
    for header in ("x-forwarded-for", "x-real-ip"):
        raw = request.headers.get(header, "")
        if raw:
            first = raw.split(",")[0].strip()
            if first:
                return first
    if request.client:
        return request.client.host or ""
    return ""


def host_from_request(request: Request) -> str:
    """浏览器访问本工具时用的 host（含反代场景的 X-Forwarded-Host）。"""
    for header in ("x-forwarded-host", "host"):
        raw = request.headers.get(header, "")
        if raw:
            host = raw.split(",")[0].strip()
            if host.startswith("["):
                host = host[: host.find("]") + 1]
            else:
                host = host.split(":")[0]
            if host and not is_loopback_host(host):
                return host
    return ""


__all__ = [
    "LOOPBACK_HOSTS",
    "is_loopback_host",
    "rewrite_loopback",
    "client_ip_from_request",
    "host_from_request",
]
