"""获取123网盘的访问令牌

采用 env 文件来管理授权信息,

- 项目级别的配置文件: `.env`
- 系统级别的配置文件: `~/.env.pan123`

如果两个文件都存在, 则优先使用项目级别的配置文件

需要去[123云盘开发平台](https://www.123pan.com/developer) 申请一个应用

配置文件参考如下
```
PAN123CLIENTID="***"
PAN123CLIENTSECRET="***"
```
当有了以上信息以后, 运行下面的代码, 会自动生成一个访问令牌, 并保存到 `.env` 文件中
```python
from cpan123 import Auth
auth = Auth()
print(auth) # 打印访问令牌

### 访问令牌会自动保存到 .env 文件中
PAN123TOKEN="**"
PAN123TOKEN_EXPIREDAT="***"
```


"""

import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests
from dotenv import find_dotenv, load_dotenv, set_key
from pydantic import dataclasses
from tenacity import retry, stop_after_attempt, wait_random

BASE_URL = "https://open-api.123pan.com"
PLATFORM = "open_platform"
HEADERS = {
    # "Authorization": "Bearer " + self.auth.access_token,
    # "Content-Type": "application/json",
    "Platform": PLATFORM,
}


def load_env():
    """加载 .env 配置(优先项目目录,其次系统目录)"""

    # 在当前目录下查找 .env 文件,找到则返回路径, 否则返回空字符串
    dotenv_path: str = find_dotenv()
    if dotenv_path:
        load_dotenv(dotenv_path, override=True)
    else:
        # 尝试从系统默认目录加载
        system_env_path = Path.home() / ".env.pan123"
        if system_env_path.exists():
            load_dotenv(system_env_path, override=True)
        else:
            return


@dataclasses.dataclass
class Auth:
    """用于获取和设置访问令牌的类.

    在每次访问 `.token` 时,会自动检查令牌是否存在或过期, 且提供了 clientID/clientSecret,就会自动刷新.  而`.access_token` 不会,是固定的值

    Attributes:
        clientID (str): 客户端 ID
        clientSecret (str): 客户端密钥
        access_token (str): 访问令牌
        access_token_expiredAt (str): 访问令牌过期时间
        token (str): 访问令牌, 每次访问时自动检查是否过期并刷新

    Example:
    ```python
    from cpan123 import Auth
    auth = Auth()
    print(auth.access_token)
    # 如果什么都没有设置, 则会自动从环境变量中加载
    # 优先从项目中目录下的 .env 文件中获取, 其次从系统目录下的 .env.pan123 文件中获取
    # 如果都没有,则会抛出异常

    # 或者手动设置
    from cpan123 import Auth
    auth = Auth(clientID="your_client_id", clientSecret="your_client_secret")
    print(auth.access_token) # 打印固定值
    # 强制刷新
    auth.refresh_access_token()
    # 会自动检查是否过期,尝试自动刷新
    print(auth.token)

    # 或者
    auth = Auth(access_token="your_access_token")
    print(auth.access_token)
    ```
    """

    clientID: Optional[str] = None
    clientSecret: Optional[str] = None

    access_token: Optional[str] = None
    access_token_expiredAt: Optional[str] = None  # ISO8601格式字符串

    def __post_init__(self) -> None:
        """
        初始化 Auth 对象
        """
        self._load_from_env()
        # 自动获取 access_token(如果未提供,但提供了 clientID 和 clientSecret)
        if not self.access_token:
            if self.clientID and self.clientSecret:
                self.refresh_access_token()
            else:
                raise ValueError("❌ No access token or client credentials found")

    def _load_from_env(self):
        """从环境变量加载认证信息"""
        load_env()
        self.clientID = self.clientID or os.getenv("PAN123CLIENTID")
        self.clientSecret = self.clientSecret or os.getenv("PAN123CLIENTSECRET")
        self.access_token = self.access_token or os.getenv("PAN123TOKEN")
        self.access_token_expiredAt = self.access_token_expiredAt or os.getenv(
            "PAN123TOKEN_EXPIREDAT"
        )

    def _is_token_expired(self) -> bool:
        """判断 access_token 是否过期"""
        if not self.access_token_expiredAt:
            return False  # 没有过期时间,认为没过期
        try:
            expire_dt = datetime.fromisoformat(self.access_token_expiredAt)
            now = datetime.now()
            return now >= expire_dt
        except ValueError:
            print("❌ Invalid access_token_expiredAt format")
            return True

    @property
    def token(self) -> str | None:
        """
        每次访问时自动检查是否过期并刷新
        """
        if self._is_token_expired():
            if self.clientID and self.clientSecret:
                print("🔁 Token 已过期,正在刷新...")
                self.refresh_access_token()
            else:
                print("⚠️ Token 已过期,缺少 clientID/clientSecret,无法刷新, 退出程序")
                sys.exit(1)

        return self.access_token

    def set_access_token(self, access_token: str) -> "Auth":
        """
        设置 access_token

        Args:
            access_token (str): 访问令牌
        """
        self.access_token = access_token
        self.access_token_expiredAt = None
        return self

    @retry(stop=stop_after_attempt(3), wait=wait_random(min=1, max=5))
    def refresh_access_token(self) -> "Auth":
        """重新获取 access_token, 或手动设置 access_token. 用于强制刷新

        强制刷新 access_token, 前提是存在 clientID 和 clientSecret.

        - 如果不存在且没有 access_token, 则退出
        - 如果不存在且有 access_token, 则不刷新access_token, 打印警告

        """
        if not self.access_token:
            if not (self.clientID and self.clientSecret):
                print("❌ No clientID/clientSecret found, and no access_token, exiting")
                sys.exit(1)
            # 有 clientID 和 clientSecret,但没有 token → 尝试刷新
            self.refresh_access_token()
        else:
            if not (self.clientID and self.clientSecret):
                print("⚠️ access_token 存在,但未提供 clientID/clientSecret,跳过刷新")
                return self
        try:
            response = requests.post(
                BASE_URL + "/api/v1/access_token",
                data={"clientID": self.clientID, "clientSecret": self.clientSecret},
                headers={"Platform": PLATFORM},
                timeout=60,
            )
            response.raise_for_status()
            data = response.json().get("data", {})
            self.access_token = data.get("accessToken")
            self.access_token_expiredAt = data.get("expiredAt")
        except Exception as e:
            print(f"❌ 请求 access_token 接口失败: {e}")
            raise

        if not self.access_token or not self.access_token_expiredAt:
            raise ValueError("❌ 获取 access_token 响应数据不完整")

        self.save_info()
        return self

    def save_info(self):
        """将 access_token 及相关信息保存到 .env 文件"""
        project_env = Path(".env")
        system_env = Path.home() / ".env.pan123"

        if project_env.exists():
            env_path = project_env
        elif system_env.exists():
            env_path = system_env
        else:
            # 默认创建项目目录下的 .env
            env_path = project_env
            env_path.touch()

        if self.clientID:
            set_key(env_path, "PAN123CLIENTID", self.clientID)
        if self.clientSecret:
            set_key(env_path, "PAN123CLIENTSECRET", self.clientSecret)
        if self.access_token:
            set_key(env_path, "PAN123TOKEN", self.access_token)
        if self.access_token_expiredAt:
            set_key(env_path, "PAN123TOKEN_EXPIREDAT", self.access_token_expiredAt)
        print(f"✅ 认证信息已保存到 {env_path} 文件中")
