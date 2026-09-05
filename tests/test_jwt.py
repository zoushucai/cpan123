import base64
import json
import time
from pathlib import Path
from unittest.mock import Mock

import httpx
from dotenv import dotenv_values

from cpan123.authtype.Jwt import Jwt


def _encode_jwt(expires_at: int) -> str:
    """创建只用于过期时间测试的无签名 JWT 字符串.

    Args:
        expires_at: 写入 ``exp`` claim 的 Unix 时间戳.

    Returns:
        包含指定 ``exp`` claim 的 JWT 字符串.
    """
    header = base64.urlsafe_b64encode(b'{"alg":"none","typ":"JWT"}').decode().rstrip("=")
    payload_data = json.dumps({"exp": expires_at}, separators=(",", ":")).encode()
    payload = base64.urlsafe_b64encode(payload_data).decode().rstrip("=")
    return f"{header}.{payload}.signature"


def _write_env(
    path: Path,
    access_token: str = "",
    expires_at: int = 0,
    trust_env: str | None = None,
) -> Path:
    """写入 JWT 客户端测试使用的环境配置.

    Args:
        path: 环境配置文件路径.
        access_token: 可选的缓存 access token.
        expires_at: 可选的缓存 Unix 过期时间戳.
        trust_env: 可选的 HTTPX 环境配置读取开关.

    Returns:
        已写入的环境配置文件路径.
    """
    lines = [
        "CLIENT_ID=test-client",
        "CLIENT_SECRET=test-secret",
        f"ACCESS_TOKEN={access_token}",
        f"EXPIRES_AT={expires_at}",
    ]
    if trust_env is not None:
        lines.append(f"TRUST_ENV={trust_env}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_is_token_valid_rejects_expired_jwt_when_cached_expiry_is_future(tmp_path):
    now = int(time.time())
    token = _encode_jwt(now - 3600)
    env_file = _write_env(tmp_path / ".env", token, now + 86400)
    client = Jwt(env_file)

    try:
        assert client.is_token_valid is False
    finally:
        client.session.close()


def test_http_client_trusts_environment_proxy_by_default(tmp_path, monkeypatch):
    """缺少 TRUST_ENV 时应兼容旧版并读取环境代理."""
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:10808")
    env_file = _write_env(tmp_path / ".env")
    client = Jwt(env_file)

    try:
        assert client.session._trust_env is True
    finally:
        client.session.close()


def test_http_client_can_ignore_environment_proxy(tmp_path, monkeypatch):
    """TRUST_ENV=false 时 JWT HTTP 客户端应忽略环境代理."""
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:10808")
    env_file = _write_env(tmp_path / ".env", trust_env="false")
    client = Jwt(env_file)

    try:
        assert client.session._trust_env is False
    finally:
        client.session.close()


def test_is_token_valid_prefers_jwt_exp_when_cached_expiry_is_past(tmp_path):
    now = int(time.time())
    token = _encode_jwt(now + 3600)
    env_file = _write_env(tmp_path / ".env", token, now - 86400)
    client = Jwt(env_file)

    try:
        assert client.is_token_valid is True
    finally:
        client.session.close()


def test_is_token_valid_falls_back_to_cached_expiry_for_opaque_token(tmp_path):
    now = int(time.time())
    env_file = _write_env(tmp_path / ".env", "opaque-access-token", now + 3600)
    client = Jwt(env_file)

    try:
        assert client.is_token_valid is True
    finally:
        client.session.close()


def test_refresh_token_persists_jwt_exp_when_api_expired_at_is_invalid(tmp_path, monkeypatch):
    jwt_expires_at = int(time.time()) + 3600
    token = _encode_jwt(jwt_expires_at)
    env_file = _write_env(tmp_path / ".env")
    client = Jwt(env_file)
    response = httpx.Response(
        200,
        json={"code": 0, "data": {"accessToken": token, "expiredAt": "invalid-date"}},
        request=httpx.Request("POST", "https://example.test/access-token"),
    )
    request_mock = Mock(return_value=response)
    monkeypatch.setattr(client, "_do_request", request_mock)

    try:
        assert client.refresh_token() == token
        saved_config = dotenv_values(env_file)
        assert client.expires_at == jwt_expires_at
        assert saved_config["EXPIRES_AT"] == str(jwt_expires_at)
        request_mock.assert_called_once()
    finally:
        client.session.close()
