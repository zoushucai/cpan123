from pathlib import Path

from dotenv import dotenv_values, find_dotenv, set_key


class EnvConfig:
    """封装 .env 文件加载、访问与保存逻辑"""

    SENSITIVE_KEYS = {"CLIENT_SECRET", "ACCESS_TOKEN", "REFRESH_TOKEN"}

    def __init__(self, envpath: str | Path | None = None, default_name: str = ".env.115"):
        self.path = self._resolve_path(envpath, default_name)
        self._config = dotenv_values(self.path)

    # -------------------- 路径处理 --------------------

    def _resolve_path(self, envpath: str | Path | None, default_name: str) -> Path:
        """解析配置文件路径，支持自动创建文件"""
        if envpath:
            path = Path(envpath).expanduser()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch(exist_ok=True)
            return path

        found = find_dotenv(usecwd=True)
        if found:
            return Path(found)

        path = Path.home() / default_name
        path.touch(exist_ok=True)
        return path

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
