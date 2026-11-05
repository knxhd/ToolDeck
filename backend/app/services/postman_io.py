"""Postman Collection v2.1 导入 / 导出转换。"""
from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any


# ---------- 导出：我们的树 → Postman v2.1 ----------

def _node_to_item(node: dict) -> dict:
    ntype = node.get("type")
    name = node.get("name") or "Untitled"
    if ntype == "folder":
        return {
            "name": name,
            "item": [_node_to_item(c) for c in (node.get("children") or [])],
        }
    if ntype == "request":
        req = node.get("request") or {}
        method = (req.get("method") or "GET").upper()
        headers = [
            {"key": h.get("key", ""), "value": h.get("value", ""), "disabled": not h.get("enabled", True)}
            for h in (req.get("headers") or [])
            if h.get("key")
        ]
        # URL 拼接
        url_raw = req.get("url") or ""
        url_obj: dict[str, Any] = {"raw": url_raw}
        if "://" in url_raw:
            proto, rest = url_raw.split("://", 1)
            url_obj["protocol"] = proto
            host_path = rest.split("/", 1)
            url_obj["host"] = host_path[0].split(".")
            if len(host_path) > 1 and host_path[1]:
                url_obj["path"] = [p for p in host_path[1].split("?")[0].split("/") if p]
        # params 作为 url.query
        params = [
            {"key": p.get("key", ""), "value": p.get("value", ""), "disabled": not p.get("enabled", True)}
            for p in (req.get("params") or [])
            if p.get("key")
        ]
        if params:
            url_obj["query"] = params
        # body
        body: dict[str, Any] = {"mode": "raw", "raw": req.get("body") or ""}
        btype = req.get("body_type")
        if btype == "json":
            body["options"] = {"raw": {"language": "json"}}
        elif btype == "xml":
            body["options"] = {"raw": {"language": "xml"}}
        elif btype == "form-data":
            body["mode"] = "formdata"
            try:
                items = json.loads(req.get("body") or "[]")
            except Exception:
                items = []
            body["formdata"] = [
                {"key": i.get("key", ""), "value": str(i.get("value", "")), "type": i.get("type", "text")}
                for i in items
            ]
        return {
            "name": name,
            "request": {
                "method": method,
                "header": headers,
                "url": url_obj,
                "body": body,
            },
            "response": [],
        }
    # collection 节点：当作一个 folder
    return {
        "name": name,
        "item": [_node_to_item(c) for c in (node.get("children") or [])],
    }


def export_collection(tree: list[dict], collection_name: str = "api-tool") -> dict:
    items = [_node_to_item(n) for n in tree]
    return {
        "info": {
            "_postman_id": str(uuid.uuid4()),
            "name": collection_name,
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
        },
        "item": items,
    }


# ---------- 导入：Postman v2.1 → 我们的树 ----------

def _url_to_str(url: Any) -> str:
    if isinstance(url, str):
        return url
    if not isinstance(url, dict):
        return ""
    raw = url.get("raw")
    if raw:
        return raw
    protocol = url.get("protocol") or "https"
    host = ".".join(url.get("host") or [])
    path = "/".join(url.get("path") or [])
    query = url.get("query") or []
    qs = "&".join(
        f"{q.get('key','')}={q.get('value','')}"
        for q in query if not q.get("disabled") and q.get("key")
    )
    return f"{protocol}://{host}" + (f"/{path}" if path else "") + (f"?{qs}" if qs else "")


def _body_type_from_mode(mode: str, options: dict) -> str:
    if mode == "raw":
        lang = (options or {}).get("raw", {}).get("language", "text")
        if lang == "json":
            return "json"
        if lang == "xml":
            return "xml"
        if lang == "html":
            return "html"
        return "text"
    if mode == "formdata":
        return "form-data"
    if mode == "urlencoded":
        return "text"
    return "none"


def _item_to_node(item: dict) -> dict | None:
    if "request" in item and isinstance(item["request"], dict):
        req_p = item["request"]
        headers = [
            {"key": h.get("key", ""), "value": h.get("value", ""), "enabled": not h.get("disabled", True)}
            for h in (req_p.get("header") or [])
            if h.get("key")
        ]
        body_raw = ""
        body_type = "none"
        body = req_p.get("body") or {}
        mode = body.get("mode") or "raw"
        if mode == "raw":
            body_raw = body.get("raw") or ""
            body_type = _body_type_from_mode(mode, body.get("options") or {})
        elif mode == "formdata":
            formdata = body.get("formdata") or []
            body_raw = json.dumps(
                [{"key": f.get("key", ""), "value": f.get("value", ""), "type": f.get("type", "text"), "enabled": True}
                 for f in formdata],
                ensure_ascii=False,
            )
            body_type = "form-data"
        elif mode == "urlencoded":
            body_raw = "&".join(
                f"{f.get('key','')}={f.get('value','')}" for f in (body.get("urlencoded") or [])
            )
            body_type = "text"

        return {
            "id": f"n_{uuid.uuid4().hex[:12]}",
            "type": "request",
            "name": item.get("name") or "Untitled",
            "kind": "http",
            "request": {
                "method": (req_p.get("method") or "GET").upper(),
                "url": _url_to_str(req_p.get("url")),
                "headers": headers or [{"key": "", "value": "", "enabled": True}],
                "params": [{"key": "", "value": "", "enabled": True}],
                "body_type": body_type,
                "body": body_raw,
            },
        }
    # folder
    children = [_item_to_node(c) for c in (item.get("item") or [])]
    children = [c for c in children if c]
    return {
        "id": f"n_{uuid.uuid4().hex[:12]}",
        "type": "folder",
        "name": item.get("name") or "Folder",
        "children": children,
    }


def import_collection(payload: dict) -> tuple[str, list[dict]]:
    """返回 (collection_name, tree)。"""
    info = payload.get("info") or {}
    name = info.get("name") or "Imported"
    items = payload.get("item") or []
    tree = [n for n in (_item_to_node(i) for i in items) if n]
    return name, tree
