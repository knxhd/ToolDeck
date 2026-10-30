# -*- coding: utf-8 -*-
"""验证 collections 字段级加密：save 加密、load 还原、migrate 迁移、DB 无明文。在临时配置目录副本上进行。"""
import os, sys, json, tempfile, shutil

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

# 使用临时配置目录，绝不触碰真实库
_tmp = tempfile.mkdtemp(prefix="api_tool_test_")
os.environ["APP_CONFIG_DIR"] = _tmp

from backend.app.services.db import init_db, get_db
from backend.app.services import collection_store as cs

init_db()
# 先建一个 user 以通过外键约束
with get_db() as c:
    c.execute(
        "INSERT INTO users(username, password_hash, display_name) VALUES('u','x','U')"
    )

HTTP_HDRS = [
    {"key": "Authorization", "value": "Bearer sk-abc-secret-token-123", "enabled": True},
    {"key": "Content-Type", "value": "application/json", "enabled": True},
]
MCP_HDRS = {"Authorization": "Bearer mcp-token-xyz"}

tree = [
    {"id": "c1", "type": "collection", "name": "c", "children": [
        {"id": "r1", "type": "request", "kind": "http", "name": "r",
         "request": {"method": "POST", "url": "https://a/b", "headers": HTTP_HDRS,
                     "params": [], "body_type": "json", "body": "{\"a\":1}"}},
        {"id": "r2", "type": "request", "kind": "mcp", "name": "m",
         "mcp_url": "https://m/", "mcp_headers": MCP_HDRS, "mcp_tool": "t", "mcp_args": {}},
    ]},
]

# 1) save 后 DB 中无明文
cs.save_collections("user", 1, tree)
with get_db() as c:
    raw = c.execute("SELECT tree_json FROM collections WHERE user_id=1").fetchone()["tree_json"]
assert "Bearer sk-abc-secret-token-123" not in raw, "HTTP 明文泄漏"
assert "Bearer mcp-token-xyz" not in raw, "MCP 明文泄漏"
assert "Content-Type" not in raw, "非敏感 header 也被一并整体加密（预期）"
assert "enc:v1:" in raw
print("OK 1) save 后 DB 无明文，headers 已整体加密")

# 2) load 还原为原始结构
got = cs.load_collections("user", 1)
req = got[0]["children"][0]
mreq = got[0]["children"][1]
assert req["request"]["headers"] == HTTP_HDRS, req["request"]["headers"]
assert mreq["mcp_headers"] == MCP_HDRS, mreq["mcp_headers"]
assert req["request"]["url"] == "https://a/b" and req["request"]["body"] == "{\"a\":1}"
print("OK 2) load 还原 headers/mcp_headers 为明文结构，其余字段不受影响")

# 3) 幂等：对已加密树再次 save 不二次加密，load 仍还原
cs.save_collections("user", 1, got)
with get_db() as c:
    raw2 = c.execute("SELECT tree_json FROM collections WHERE user_id=1").fetchone()["tree_json"]
assert raw2.count("enc:v1:") == raw.count("enc:v1:"), "重复 save 二次加密了"
assert cs.load_collections("user", 1)[0]["children"][0]["request"]["headers"] == HTTP_HDRS
print("OK 3) 幂等：重复 save 不叠加加密，load 仍还原")

# 4) 迁移：构造一条明文 tree 入库（模拟旧数据），migrate 后变密文且可还原
with get_db() as c:
    c.execute("UPDATE collections SET tree_json=? WHERE user_id=1", (json.dumps(tree, ensure_ascii=False),))
cs.migrate_collections_secrets()
with get_db() as c:
    raw3 = c.execute("SELECT tree_json FROM collections WHERE user_id=1").fetchone()["tree_json"]
assert "Bearer sk-abc-secret-token-123" not in raw3 and "Bearer mcp-token-xyz" not in raw3
assert cs.load_collections("user", 1)[0]["children"][0]["request"]["headers"] == HTTP_HDRS
cs.migrate_collections_secrets()  # 再次迁移应幂等
print("OK 4) migrate 将存量明文转密文，可还原，且幂等")

shutil.rmtree(_tmp, ignore_errors=True)
print("ALL COLLECTIONS CHECKS PASSED")
