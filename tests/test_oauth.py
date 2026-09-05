from pathlib import Path

import pytest

from cpan123.authtype.OAuth import OAuth


def _write_env(path: Path, trust_env: str | None) -> Path:
    """写入 OAuth 客户端测试使用的环境配置.

    Args:
        path: 环境配置文件路径.
        trust_env: 可选的 HTTPX 环境配置读取开关.
    Returns:
        已写入的环境配置文件路径.
    """
    lines = ["CLIENT_ID=test-client"]
    if trust_env is not None:
        lines.append(f"TRUST_ENV={trust_env}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


@pytest.mark.parametrize(("configured_value", "expected"), [(None, True), ("false", False)])
def test_oauth_http_client_respects_trust_env(tmp_path, configured_value, expected):
    """OAuth HTTP 客户端应使用兼容默认值并支持显式关闭环境代理."""
    client = OAuth(_write_env(tmp_path / ".env", configured_value))

    try:
        assert client.session._trust_env is expected
    finally:
        client.session.close()
