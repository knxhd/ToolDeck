# -*- coding: utf-8 -*-
"""验证字段级加密：crypto DPAPI 往返、config 加解密、历史表迁移（在副本上）。
通过 stub fastapi 让 backend.app 包可导入（仅测试用）。"""
import os, sys, json, sqlite3, shutil, importlib.util

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

# --- stub fastapi 以便导入 backend.app.config / history_store ---
import types
_fake_fastapi = types.ModuleType("fastapi")
_fake_responses = types.ModuleType("fastapi.responses")
_fake_static = types.ModuleType("fastapi.staticfiles")
_fake_cors = types.ModuleType("fastapi.middleware")
_fake_cors_mod = types.ModuleType("fastapi.middleware.cors")
class _FastAPI: title=""; version=""
class _CORSMiddleware: pass
class _HTMLResponse:
    def __init__(self, *a, **k): pass
class _JSONResponse: pass
class _StaticFiles: pass
_fake_cors_mod.CORSMiddleware = _CORSMiddleware
_fake_responses.HTMLResponse = _HTMLResponse
_fake_responses.JSONResponse = _JSONResponse
_fake_static.StaticFiles = _StaticFiles
_fake_fastapi.FastAPI = _FastAPI
_fake_fastapi.responses = _fake_responses
_fake_fastapi.staticfiles = _fake_static
_fake_fastapi.middleware = _fake_cors
sys.modules["fastapi"] = _fake_fastapi
sys.modules["fastapi.responses"] = _fake_responses
sys.modules["fastapi.staticfiles"] = _fake_static
sys.modules["fastapi.middleware"] = _fake_cors
sys.modules["fastapi.middleware.cors"] = _fake_cors_mod

from backend.app.services import crypto
from backend.app.config import _encrypt_sensitive, _decrypt_sensitive, load_config
from backend.app.services import history_store

# 1) crypto 往返 + 历史明文兼容
for s in ["sk-abc123XYZ", '{"Authorization":"Bearer abc.def"}', "", "普通中文值 測試"]:
    e = crypto.encrypt(s); d = crypto.decrypt(e)
    assert d == s, f"roundtrip fail: {s!r} -> {d!r}"
    assert crypto.is_encrypted(e)
    print(f"crypto OK: {s!r} -> {e[:38]}... len={len(e)}")
assert crypto.decrypt("plain-未加密") == "plain-未加密"
assert not crypto.is_encrypted("plain-未加密")
print("crypto plaintext-compat OK")

# 2) config 加解密对称（不写回真实文件）
data = load_config()
print("config providers/mcp:", len(data.get("llm_providers", [])), len(data.get("mcp_servers", [])))
demo = {"llm_providers": [{"name": "p", "api_key": "sk-明文-123", "model": "gpt"}],
        "mcp_servers": [{"name": "m", "url": "x", "headers": {"Authorization": "Bearer tok"}}]}
enc = _encrypt_sensitive(json.loads(json.dumps(demo)))
assert crypto.is_encrypted(enc["llm_providers"][0]["api_key"])
assert crypto.is_encrypted(enc["mcp_servers"][0]["headers"]["Authorization"])
dec = _decrypt_sensitive(enc)
assert dec["llm_providers"][0]["api_key"] == "sk-明文-123"
assert dec["mcp_servers"][0]["headers"]["Authorization"] == "Bearer tok"
# 幂等：已是密文不叠加前缀，解密仍回原文（DPAPI 每次盐不同，不比字节）
enc2 = _encrypt_sensitive(json.loads(json.dumps(enc)))
assert enc2["llm_providers"][0]["api_key"].startswith("enc:v1:")
assert not enc2["llm_providers"][0]["api_key"].startswith("enc:v1:enc:v1:")
dec2 = _decrypt_sensitive(enc2)
assert dec2 == demo, "not idempotent round-trip"
print("config encrypt/decrypt + idempotent OK")

# 3) 历史表迁移：在真实库副本上执行与 migrate_history_secrets 相同的 SQL
real = os.path.join(os.path.expanduser("~"), ".api-tool", "api-tool.db")
copy = os.path.join(os.path.dirname(__file__), "_test_copy.db")
shutil.copy(real, copy)
c = sqlite3.connect(copy)
c.execute("INSERT INTO http_history(user_id,method,url,headers_json,body_type,body) VALUES(1,'GET','u','[{\"key\":\"Authorization\",\"value\":\"Bearer xxx\"}]','json','{\"a\":1}')")
c.execute("INSERT INTO llm_history(user_id,provider,model,messages_json,content) VALUES(1,'p','m','[{\"role\":\"user\",\"content\":\"hi\"}]','resp')")
c.commit()
for table, cols in history_store._ENCRYPTED_COLUMNS.items():
    for col in cols:
        rows = c.execute(f"SELECT id, {col} FROM {table} WHERE {col} IS NOT NULL").fetchall()
        for rid, val in rows:
            if isinstance(val, str) and not crypto.is_encrypted(val):
                c.execute(f"UPDATE {table} SET {col}=? WHERE id=?", (crypto.encrypt(val), rid))
c.commit()
for table, cols in history_store._ENCRYPTED_COLUMNS.items():
    for col in cols:
        rows = c.execute(f"SELECT {col} FROM {table} WHERE {col} IS NOT NULL").fetchall()
        for (v,) in rows:
            assert crypto.is_encrypted(v), f"{table}.{col} still plaintext"
            crypto.decrypt(v)
        print(f"migration {table}.{col}: {len(rows)} rows encrypted OK")
c.close(); os.remove(copy)
print("ALL CHECKS PASSED")
