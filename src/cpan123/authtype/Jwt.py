import time
from datetime import datetime

import httpx

from ..model.Base import AuthError
from ..utils.Constants import API, UA
from ..utils.EnvConfig import EnvConfig
from ..utils.Logger import log, log_request, log_response


class Jwt:
    """JWT 授权与 Token 管理, JWT授权一般没有refresh_token, 直接通过 client_id 和 client_secret 获取token"""

    REFRESH_THRESHOLD = 60  # 提前刷新秒数

    def __init__(self, envpath: str | None = None, verbose: bool = False):
        """
        JWT 授权与 Token 管理

        Args:
            envpath: .env 文件路径, 如果为 None 则使用当前目录下的 .env
            verbose: 是否启用详细日志输出
        """
        self.env = EnvConfig(envpath)
        self.verbose = verbose
        self._load_config()
        self.session = self._create_client()

    # -------------------- 配置 --------------------
    def _load_config(self):
        env = self.env
        self.client_id = env.get("CLIENT_ID")
        self.client_secret = env.get("CLIENT_SECRET")
        self.access_token = env.get("ACCESS_TOKEN")
        self.expires_at = env.get_int("EXPIRES_AT", 0)

    # -------------------- HTTP 客户端 --------------------
    def _create_client(self) -> httpx.Client:
        hooks = {"request": [log_request], "response": [log_response]} if self.verbose else None
        return httpx.Client(headers={"User-Agent": UA}, timeout=30, event_hooks=hooks)

    # def _is_iso8601_format(self, date_str):
    #     try:
    #         datetime.fromisoformat(date_str)
    #         return True
    #     except ValueError:
    #         return False
    # -------------------- Token 管理 --------------------
    # def _expire2int(self, expire_value: str | int | float) -> int:
    #     """将过期时间值转换为整数秒"""
    #     if isinstance(expire_value, int):
    #         t = expire_value
    #     elif isinstance(expire_value, (str, float)):
    #         try:
    #             t = int(float(expire_value))
    #         except (TypeError, ValueError):
    #             log.error(f"无法将过期时间转换为整数: {expire_value}")
    #             raise AuthError(-1, "无效的过期时间格式") from None
    #     else:
    #         log.error(f"过期时间值类型不支持: {type(expire_value)}")
    #         raise AuthError(-1, "无效的过期时间类型")
    #     if t < 0 or t >= 20 * 365 * 24 * 3600:
    #         log.error(f"过期时间数值异常: {t}")
    #         raise AuthError(-1, "过期时间数值异常")
    #     return t
    @property
    def is_token_valid(self) -> bool:
        return self.expires_at > time.time() + self.REFRESH_THRESHOLD

    def _get_key(self, data: dict, key: str) -> str:
        """从响应数据中获取指定 key 的值，支持多层嵌套"""
        return data.get(key) or data.get("data", {}).get(key) or ""

    def _fetch_token(self) -> None:
        """通过 client_id/secret 获取新的 access_token"""
        if not self.client_id or not self.client_secret:
            raise AuthError(-1, "缺少 client_id 或 client_secret，无法刷新 token")

        data = {
            "clientID": self.client_id,
            "clientSecret": self.client_secret,
        }
        headers = {"Platform": "open_platform"}
        respjson = self._do_request("POST", url=API.JWT.TOKEN, headers=headers, data=data).json()
        self._update_token(respjson)

    def _update_token(self, data: dict):
        """更新本地 token 并写回 .env"""
        code = int(self._get_key(data, "code") or 0)
        if code != 0:
            raise AuthError(int(code), f"获取 token 失败: {data}")
        access_token = self._get_key(data, "accessToken")
        expiredAt = self._get_key(data, "expiredAt")

        try:
            expires_in = int(datetime.fromisoformat(expiredAt).timestamp())
        except (TypeError, ValueError):
            log.error(f"无法将过期时间转换为整数: {expiredAt}")
            raise AuthError(-1, "无效的过期时间格式") from None

        if not access_token:
            raise AuthError(-1, "响应缺少 access_token")

        self.access_token = access_token
        self.expires_at = expires_in

        for k, v in {
            "ACCESS_TOKEN": access_token,
            "EXPIRES_AT": str(int(self.expires_at)),
        }.items():
            self.env.set(k, v)

    # -------------------- 请求方法 --------------------
    def _do_request(self, method: str, url: str, **kwargs) -> httpx.Response:
        try:
            resp = self.session.request(method, url, **kwargs)
            resp.raise_for_status()
            return resp
        except httpx.RequestError as e:
            log.error(f"method: {method}, url: {url}, 网络请求失败: {e}")
            raise AuthError(-1, f"网络错误: {e}") from e
        except httpx.HTTPStatusError as e:
            raise AuthError(e.response.status_code, f"HTTP 错误: {e}") from e

    # -------------------- Token 自动获取 --------------------
    def _get_token_if_needed(self) -> str:
        if not self.access_token or not self.is_token_valid:
            self._fetch_token()
        return self.access_token

    def refresh_token(self) -> str:
        """强制刷新 access_token"""
        self._fetch_token()
        return self.access_token

    # -------------------- 公共接口 --------------------
    def get_access_token(self) -> str:
        """获取有效的 access_token, 如果过期则自动刷新"""
        access_token = self._get_token_if_needed()
        if not access_token:
            raise AuthError(40140116, "无法获取有效的 access_token")
        return access_token
