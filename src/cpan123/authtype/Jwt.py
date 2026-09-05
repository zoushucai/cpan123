import base64
import binascii
import json
import math
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
            envpath: 环境文件路径。未指定时按优先级查找：CPAN123_ENV > 当前目录 .env > 用户目录 .env.123
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
        self.trust_env = env.get_bool("TRUST_ENV", True)

    # -------------------- HTTP 客户端 --------------------
    def _create_client(self) -> httpx.Client:
        hooks = {"request": [log_request], "response": [log_response]} if self.verbose else None
        timeout = httpx.Timeout(connect=30.0, read=120.0, write=120.0, pool=30.0)
        return httpx.Client(
            headers={"User-Agent": UA},
            timeout=timeout,
            event_hooks=hooks,
            trust_env=self.trust_env,
        )

    # -------------------- Token 管理 --------------------
    @property
    def is_token_valid(self) -> bool:
        jwt_expires_at = self._get_jwt_expires_at(self.access_token)
        effective_expires_at = jwt_expires_at if jwt_expires_at is not None else self.expires_at
        return effective_expires_at > time.time() + self.REFRESH_THRESHOLD

    @staticmethod
    def _get_jwt_expires_at(access_token: str | None) -> int | None:
        """读取 JWT payload 中的过期时间.

        此处仅使用 ``exp`` 判断何时刷新 token，不负责验证 JWT 签名。对于非 JWT、
        payload 损坏或缺少有效 ``exp`` 的 token，返回 ``None``，由调用方回退到
        服务端返回的 ``expiredAt``。

        Args:
            access_token: 待解析的 access token.

        Returns:
            JWT 的 Unix 过期时间戳；无法解析时返回 ``None``.
        """
        if not access_token:
            return None

        parts = access_token.split(".")
        if len(parts) != 3:
            return None

        encoded_payload = parts[1]
        padded_payload = encoded_payload + "=" * (-len(encoded_payload) % 4)
        try:
            payload = json.loads(base64.urlsafe_b64decode(padded_payload).decode("utf-8"))
        except (binascii.Error, json.JSONDecodeError, UnicodeDecodeError, ValueError):
            return None

        if not isinstance(payload, dict):
            return None

        expires_at = payload.get("exp")
        if isinstance(expires_at, bool) or not isinstance(expires_at, int | float):
            return None
        if not math.isfinite(expires_at):
            return None
        return int(expires_at)

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

        if not access_token:
            raise AuthError(-1, "响应缺少 access_token")

        jwt_expires_at = self._get_jwt_expires_at(access_token)
        if jwt_expires_at is not None:
            expires_at = jwt_expires_at
        else:
            expired_at = self._get_key(data, "expiredAt")
            try:
                expires_at = int(datetime.fromisoformat(expired_at).timestamp())
            except (TypeError, ValueError):
                log.error(f"无法将过期时间转换为整数: {expired_at}")
                raise AuthError(-1, "无效的过期时间格式") from None

        self.access_token = access_token
        self.expires_at = expires_at

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
