import warnings
from pathlib import Path

from dotenv import dotenv_values, set_key


class EnvConfig:
    """封装 .env 文件加载、访问与保存逻辑"""

    SENSITIVE_KEYS = {"CLIENT_SECRET", "ACCESS_TOKEN", "REFRESH_TOKEN"}

    def __init__(self, envpath: str | Path | None = None, default_name: str = ".env.123"):
        self.path = self._resolve_path(envpath, default_name)
        self._config = dotenv_values(self.path)

    # -------------------- 路径处理 --------------------

    def _resolve_path(self, envpath: str | Path | None, default_name: str) -> Path:
        """解析配置文件路径。

        优先级：用户指定路径 > 当前目录 .env > 用户目录 default_name。
        """
        if envpath:
            path = Path(envpath).expanduser()
            if not path.exists():
                raise FileNotFoundError(
                    f"指定的环境文件不存在: {path}\n\n"
                    f"请使用以下任一方式配置：\n"
                    f"1) 通过 envpath 指向已存在的配置文件\n"
                    f"2) 在当前目录创建 .env ({(Path.cwd() / '.env').resolve()})\n"
                    f"3) 在用户目录创建 {default_name} ({Path.home() / default_name})"
                )
            return path

        cwd_env = Path.cwd() / ".env"
        if cwd_env.exists():
            if self._has_required_auth_keys(cwd_env):
                return cwd_env
            warnings.warn(
                f"检测到当前目录配置文件 {cwd_env}，但缺少 CLIENT_ID 或 CLIENT_SECRET，将继续尝试用户目录配置文件 {Path.home() / default_name}。",
                stacklevel=2,
            )

        path = Path.home() / default_name
        if path.exists():
            if self._has_required_auth_keys(path):
                return path
            warnings.warn(
                f"检测到用户目录配置文件 {path}，但缺少 CLIENT_ID 或 CLIENT_SECRET。",
                stacklevel=2,
            )

        raise FileNotFoundError(
            "未找到环境配置文件。\n\n"
            "查找优先级：\n"
            "- 用户指定路径 envpath\n"
            f"- 当前目录 .env ({cwd_env.resolve()})\n"
            f"- 用户目录 {default_name} ({path})\n\n"
            "注意：若文件存在但缺少 CLIENT_ID 或 CLIENT_SECRET，也会被视为无效。\n\n"
            "请使用以下任一方式配置：\n"
            "1) 初始化客户端时传入 envpath，指向你的配置文件\n"
            f"2) 在当前运行目录创建 .env ({cwd_env.resolve()})\n"
            f"3) 在用户目录创建 {default_name} ({path})\n\n"
            "配置文件至少应包含：CLIENT_ID、CLIENT_SECRET"
        )

    def _has_required_auth_keys(self, path: Path) -> bool:
        cfg = dotenv_values(path)
        client_id = (cfg.get("CLIENT_ID") or "").strip()
        client_secret = (cfg.get("CLIENT_SECRET") or "").strip()
        return bool(client_id and client_secret)

    # -------------------- 配置访问 --------------------

    def get(self, key: str, default: str = "") -> str:
        """获取配置项，若不存在则返回默认值"""
        return (self._config.get(key) or default).strip()

    def set(self, key: str, value: str):
        """设置配置项并保存到文件"""
        set_key(str(self.path), key, value)
        self._config[key] = value

    def require(self, key: str, errmsg: str | None = None) -> str:
        """获取必须存在的配置项，若不存在则抛出异常"""
        val = self.get(key)
        if not val:
            raise ValueError(errmsg or f"缺少必要配置项: {key}")
        return val

    def get_int(self, key: str, default: int = 0) -> int:
        """获取整数配置项，若不存在或无法转换则返回默认值"""
        val = self.get(key)
        try:
            return int(val)
        except ValueError:
            return default

    def as_dict(self) -> dict:
        """以字典形式返回所有配置项"""
        return dict(self._config)

    # -------------------- 打印与调试 --------------------
    def __repr__(self):
        """控制台友好显示：隐藏敏感信息"""
        masked = {k: ("***" if k in self.SENSITIVE_KEYS and v else v) for k, v in self._config.items()}
        return f"<EnvConfig path='{self.path}' values={masked}>"

    def __str__(self):
        """更简短的输出（例如 print(env) 时）"""
        safe_items = []
        for k, v in self._config.items():
            if k in self.SENSITIVE_KEYS:
                safe_items.append(f"{k}=***")
            else:
                safe_items.append(f"{k}={v}")
        return f"EnvConfig({self.path}): " + ", ".join(safe_items)
