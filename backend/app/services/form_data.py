"""Form Data 请求体解析：把前端保存的 JSON 数组转换为 httpx 可用的 data / files。

前端 body（body_type = form-data）格式：
    [{"key": "name", "value": "tom", "type": "text", "enabled": true},
     {"key": "avatar", "value": "D:/data/a.png", "type": "file", "enabled": true}]

- type 缺省视为 text；enabled 缺省视为 true（兼容旧数据）。
- file 项的 value 是本机文件路径，发送时读取文件内容，以 multipart/form-data 上传。
- 只有 text 项时保持 application/x-www-form-urlencoded（与旧行为一致）。
"""
from __future__ import annotations

import json
import mimetypes
from pathlib import Path
from typing import Any

FormFields = dict[str, Any]
FormFiles = list[tuple[str, tuple[str, bytes, str]]]


class FormDataError(ValueError):
    """Form Data 解析失败（如文件不存在），消息可直接展示给用户。"""


def _normalize_path(raw: str) -> Path:
    # 兼容从资源管理器「复制为路径」带出的双引号
    return Path(raw.strip().strip('"').strip("'")).expanduser()


def build_form_data(body: str) -> tuple[FormFields, FormFiles]:
    """解析 form-data body，返回 (文本字段, 文件字段)。

    文本字段为 dict：同名多值时 value 为 list（httpx 要求 Mapping）。
    """
    try:
        items = json.loads(body) if body else []
    except json.JSONDecodeError:
        return {}, []
    if not isinstance(items, list):
        return {}, []

    fields: FormFields = {}
    files: FormFiles = []
    for item in items:
        if not isinstance(item, dict) or not item.get("key"):
            continue
        if item.get("enabled") is False:
            continue
        key = str(item["key"])
        value = str(item.get("value") or "")

        if item.get("type") == "file":
            if not value.strip():
                raise FormDataError(f"Form Data 字段「{key}」未选择文件")
            path = _normalize_path(value)
            if not path.is_file():
                raise FormDataError(f"Form Data 字段「{key}」的文件不存在：{value}")
            mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            files.append((key, (path.name, path.read_bytes(), mime)))
            continue

        if key in fields:
            existing = fields[key]
            fields[key] = [*existing, value] if isinstance(existing, list) else [existing, value]
        else:
            fields[key] = value
    return fields, files


def drop_content_type(headers: dict[str, str]) -> dict[str, str]:
    """上传文件时移除用户手写的 Content-Type，交由 httpx 生成带 boundary 的 multipart 头。"""
    return {k: v for k, v in headers.items() if k.lower() != "content-type"}


__all__ = ["FormDataError", "build_form_data", "drop_content_type"]
