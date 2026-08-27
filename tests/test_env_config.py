from pathlib import Path

import pytest

from cpan123.utils.EnvConfig import EnvConfig


def _write_env(path: Path, client_id: str) -> Path:
    """写入测试使用的环境配置文件.

    Args:
        path: 环境配置文件路径.
        client_id: 写入的客户端 ID.
    Returns:
        已写入的环境配置文件路径.
    """
    path.write_text(f"CLIENT_ID={client_id}\nCLIENT_SECRET=secret\n", encoding="utf-8")
    return path


def test_env_config_uses_cpan123_env_when_path_is_not_explicit(tmp_path, monkeypatch):
    env_file = _write_env(tmp_path / "from-environment.env", "environment")
    monkeypatch.setenv("CPAN123_ENV", str(env_file))

    config = EnvConfig()

    assert config.path == env_file
    assert config.get("CLIENT_ID") == "environment"


def test_env_config_explicit_path_takes_priority_over_cpan123_env(tmp_path, monkeypatch):
    explicit_file = _write_env(tmp_path / "explicit.env", "explicit")
    environment_file = _write_env(tmp_path / "from-environment.env", "environment")
    monkeypatch.setenv("CPAN123_ENV", str(environment_file))

    config = EnvConfig(explicit_file)

    assert config.path == explicit_file
    assert config.get("CLIENT_ID") == "explicit"


def test_env_config_reports_missing_cpan123_env_file(tmp_path, monkeypatch):
    missing_file = tmp_path / "missing.env"
    monkeypatch.setenv("CPAN123_ENV", str(missing_file))

    with pytest.raises(FileNotFoundError, match="环境变量 CPAN123_ENV"):
        EnvConfig()
