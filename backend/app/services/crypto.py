"""字段级敏感数据加密。

设计目标：敏感字段（api_key、headers、消息体等）落盘时为密文，读取时解密。
密钥不随数据文件一起明文存放：

- Windows：使用系统 DPAPI（CryptProtectData / CryptUnprotectData）直接加密每个字段。
  密钥由 Windows 按“当前用户 + 本机”绑定，密文被拷贝到其它机器或其它账号后无法解开，
  且不引入任何第三方依赖。
- 非 Windows（Linux/macOS）：使用 Fernet(AES)，密钥来自环境变量 API_TOOL_MASTER_KEY，
  否则自动生成到 ~/.api-tool/.master.key（0600）。需要安装 cryptography。

密文统一带前缀 ``enc:v1:``，便于区分密文与历史明文（迁移兼容）。
"""
from __future__ import annotations

import base64
import os
from pathlib import Path

_PREFIX = "enc:v1:"

_WIN = os.name == "nt"

if _WIN:
    import ctypes
    from ctypes import wintypes, POINTER, byref, cast, c_void_p, create_string_buffer

    _CRYPTPROTECT_UI_FORBIDDEN = 0x1

    class _DATA_BLOB(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", POINTER(ctypes.c_char))]

    _crypt32 = ctypes.windll.crypt32
    _crypt32.CryptProtectData.restype = wintypes.BOOL
    _crypt32.CryptProtectData.argtypes = [
        POINTER(_DATA_BLOB),  # pDataIn
        wintypes.LPCWSTR,     # szDataDescr（可为 None）
        POINTER(_DATA_BLOB),  # pOptionalEntropy
        c_void_p,             # pvReserved
        c_void_p,             # pPromptStruct
        wintypes.DWORD,       # dwFlags
        POINTER(_DATA_BLOB),  # pDataOut
    ]
    _crypt32.CryptUnprotectData.restype = wintypes.BOOL
    _crypt32.CryptUnprotectData.argtypes = [
        POINTER(_DATA_BLOB),          # pDataIn
        POINTER(wintypes.LPWSTR),     # ppszDataDescr
        POINTER(_DATA_BLOB),          # pOptionalEntropy
        c_void_p,                     # pvReserved
        c_void_p,                     # pPromptStruct
        wintypes.DWORD,               # dwFlags
        POINTER(_DATA_BLOB),          # pDataOut
    ]
    _crypt32.LocalFree = ctypes.windll.kernel32.LocalFree
    _crypt32.LocalFree.restype = c_void_p
    _crypt32.LocalFree.argtypes = [c_void_p]


def _protect_win(data: bytes) -> bytes:
    buf = create_string_buffer(data)
    blob_in = _DATA_BLOB(len(data), cast(buf, POINTER(ctypes.c_char)))
    blob_out = _DATA_BLOB()
    if not _crypt32.CryptProtectData(
        byref(blob_in), None, None, None, None, _CRYPTPROTECT_UI_FORBIDDEN, byref(blob_out)
    ):
        raise OSError("CryptProtectData 失败")
    try:
        return ctypes.string_at(blob_out.pbData, blob_out.cbData)
    finally:
        _crypt32.LocalFree(blob_out.pbData)


def _unprotect_win(data: bytes) -> bytes:
    buf = create_string_buffer(data)
    blob_in = _DATA_BLOB(len(data), cast(buf, POINTER(ctypes.c_char)))
    blob_out = _DATA_BLOB()
    if not _crypt32.CryptUnprotectData(byref(blob_in), None, None, None, None, 0, byref(blob_out)):
        raise OSError("CryptUnprotectData 失败")
    try:
        return ctypes.string_at(blob_out.pbData, blob_out.cbData)
    finally:
        _crypt32.LocalFree(blob_out.pbData)


def _fernet():
    """非 Windows 兜底：Fernet(AES)，密钥来自环境变量或 ~/.api-tool/.master.key。"""
    try:
        from cryptography.fernet import Fernet
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "非 Windows 平台加密需要安装 cryptography（pip install cryptography），"
            "或设置环境变量 API_TOOL_MASTER_KEY 使用 DPAPI 之外的方式。"
        ) from exc
    key = _load_or_create_key()
    return Fernet(key)


def _load_or_create_key() -> bytes:
    env = os.environ.get("API_TOOL_MASTER_KEY")
    if env:
        return env.encode()
    key_path = Path.home() / ".api-tool" / ".master.key"
    if key_path.exists():
        return key_path.read_bytes()
    from cryptography.fernet import Fernet

    key = Fernet.generate_key()
    key_path.parent.mkdir(parents=True, exist_ok=True)
    key_path.write_bytes(key)
    try:
        os.chmod(key_path, 0o600)
    except OSError:
        pass
    return key


def is_encrypted(value) -> bool:
    """判断一个字符串是否已是本模块产出的密文。"""
    return isinstance(value, str) and value.startswith(_PREFIX)


def encrypt(plaintext: str | None) -> str | None:
    """明文 -> 密文（带前缀）。None 原样返回。"""
    if plaintext is None:
        return None
    data = plaintext.encode("utf-8")
    blob = _protect_win(data) if _WIN else _fernet().encrypt(data)
    return _PREFIX + base64.urlsafe_b64encode(blob).decode()


def decrypt(token: str | None) -> str | None:
    """密文 -> 明文。若传入的不是本模块密文（历史明文），原样返回（迁移兼容）。"""
    if token is None:
        return None
    if not is_encrypted(token):
        return token
    blob = base64.urlsafe_b64decode(token[len(_PREFIX):])
    data = _unprotect_win(blob) if _WIN else _fernet().decrypt(blob)
    return data.decode("utf-8")


__all__ = ["encrypt", "decrypt", "is_encrypted"]
