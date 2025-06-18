import re
from pathlib import Path
from typing import Any

from dotenv import find_dotenv, load_dotenv


def load_env():
    """加载 .env 配置(优先项目目录,其次系统目录)"""

    # 在当前目录下查找 .env 文件,找到则返回路径, 否则返回空字符串
    dotenv_path: str = find_dotenv()
    if dotenv_path:
        load_dotenv(dotenv_path, override=True)
    else:
        # 尝试从系统默认目录加载
        system_env_path = Path.home() / ".env.pan123"
        # print(f"尝试从系统目录加载环境变量: {system_env_path}")
        if system_env_path.exists():
            load_dotenv(system_env_path, override=True)
        else:
            return


BASE_URL = "https://open-api.123pan.com"
PLATFORM = "open_platform"
HEADERS = {
    # "Authorization": "Bearer " + self.auth.access_token,
    # "Content-Type": "application/json",
    "Platform": PLATFORM,
}

TYPE_MAP = {
    "int": int,
    "float": float,
    "str": str,
    "number": float,
    "string": str,
    "bool": bool,
    "boolean": bool,
    "list": list,
    "dict": dict,
    "object": dict,
    "array": list,
    "any": Any,
    "none": type(None),
    "null": type(None),
}
DEFAULT_BY_TYPE = {
    "int": 0,
    "float": 0.0,
    "str": "",
    "string": "",
    "number": 0.0,
    "bool": False,
    "boolean": False,
    "list": [],
    "dict": {},
}
TEMPLATE_PATTERN = re.compile(r"{{\s*([\w\.]+)\s*}}", re.IGNORECASE)
EMBEDDED_TEMPLATE_PATTERN = re.compile(r"{{{\s*([\w\.]+)\s*}}}", re.IGNORECASE)
