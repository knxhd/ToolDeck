"""端口探测：在 [start, end] 区间寻找可用端口。"""
from __future__ import annotations

import socket


def find_available_port(start: int = 8765, end: int = 8775) -> int:
    """通过 socket.bind 探测 [start, end] 区间内第一个可用端口。

    Args:
        start: 起始端口（默认 8765）
        end: 结束端口（默认 8775）

    Returns:
        第一个可绑定的端口

    Raises:
        RuntimeError: 所有端口均被占用
    """
    for port in range(start, end + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError(f"无可用端口，请释放 {start}-{end} 范围内端口后重试")


__all__ = ["find_available_port"]
