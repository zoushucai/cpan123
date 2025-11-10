import time
from urllib.parse import urlencode, urljoin

import httpx

from ..model.Base import AuthError
from ..utils.Constants import API, UA
from ..utils.EnvConfig import EnvConfig  # 假设上面的类放在 config.py 中
from ..utils.Logger import log, log_request, log_response


class OAuth:
    """OAuth2 授权与 Token 管理"""

    # 默认客户端 ID
    DEFAULT_CLIENT_ID = "100197735"
    # 默认后端 URL
    DEFAULT_BACKEND_URL = "https://open.xiaocai.site"
    # 默认回调 URL
    DEFAULT_REDIRECT_URI = "https://open.xiaocai.site"
    REFRESH_THRESHOLD = 60

    def __init__(self, envpath: str | None = None, verbose: bool = False):
        """初始化 OAuthClient


        Args:
            envpath: .env 文件路径, 如果为 None 则使用当前目录下的 .env
            verbose: 是否启用详细日志输出


        """
        self.env = EnvConfig(envpath)
        self.verbose = verbose
        self._load_config()

        # -------------------- HTTP 客户端 --------------------
        self.session = self._create_client()
        self._state = ""

    def _load_config(self):
        """从环境加载并解析所有关键配置"""
        env = self.env

        # 环境区分
        self.is_dev = env.get("ENV", "production").lower() in ("dev", "development")

        # 后端 URL
        self.backend_oauth_url = env.get("BACKEND_OAUTH_URL_DEV") if self.is_dev else env.get("BACKEND_OAUTH_URL", self.DEFAULT_BACKEND_URL)

        # client 相关
        self.client_secret = env.get("CLIENT_SECRET")
        self.client_id = env.require("CLIENT_ID", "CLIENT_ID 必须设置") if self.client_secret else env.get("CLIENT_ID", self.DEFAULT_CLIENT_ID)
        self.redirect_uri = env.require("REDIRECT_URI", "REDIRECT_URI 必须设置") if self.client_secret else env.get("REDIRECT_URI", self.DEFAULT_REDIRECT_URI)

        # token 相关
        self.access_token = env.get("ACCESS_TOKEN")
        self.refresh_token = env.get("REFRESH_TOKEN")
        self.expires_at = env.get_int("EXPIRES_AT")

    # ==========================================================
    # HTTP 客户端与日志
    # ==========================================================

    def _create_client(self) -> httpx.Client:
        if self.verbose:
            hooks = {"request": [log_request], "response": [log_response]}
        else:
            hooks = None
        return httpx.Client(headers={"User-Agent": UA}, timeout=30, event_hooks=hooks)

    # ==========================================================
    # Token 管理
    # ==========================================================

    @property
    def is_token_valid(self) -> bool:
        return self.expires_at > time.time() + self.REFRESH_THRESHOLD

    def _expire2int(self, expire_value: str | int | float | None) -> int:
        """将过期时间值转换为整数秒"""
        if not expire_value:
            log.error("过期时间值为空")
            raise AuthError(-1, "过期时间不能为空")

        if isinstance(expire_value, int):
            t = expire_value
        elif isinstance(expire_value, (str, float)):
            try:
                t = int(float(expire_value))
            except (TypeError, ValueError):
                log.error(f"无法将过期时间转换为整数: {expire_value}")
                raise AuthError(-1, "无效的过期时间格式") from None
        else:
            log.error(f"过期时间值类型不支持: {type(expire_value)}")
            raise AuthError(-1, "无效的过期时间类型")

        if t < 0 or t >= 20 * 365 * 24 * 3600:
            log.error(f"过期时间数值异常: {t}")
            raise AuthError(-1, "过期时间数值异常")

        return t

    def _get_key(self, data: dict, key: str) -> str:
        """从响应数据中获取指定 key 的值，支持多层嵌套"""
        return data.get(key) or data.get("data", {}).get(key) or ""

    def _update_token(self, data: dict):
        """更新本地 token 并写回 .env"""
        access_token = self._get_key(data, "access_token")
        refresh_token = self._get_key(data, "refresh_token")
        expires_in = self._get_key(data, "expires_in")

        expires_in = self._expire2int(expires_in)

        if not access_token or not refresh_token:
            raise AuthError(-1, "响应缺少 access_token 或 refresh_token")

        self.access_token = access_token
        self.refresh_token = refresh_token
        self.expires_at = time.time() + expires_in

        for k, v in {
            "ACCESS_TOKEN": access_token,
            "REFRESH_TOKEN": refresh_token,
            "EXPIRES_AT": str(int(self.expires_at)),
        }.items():
            self.env.set(k, v)

    # ==========================================================
    # OAuth 流程
    # ==========================================================

    def _do_request(self, method: str, url: str, **kwargs) -> httpx.Response:
        try:
            resp = self.session.request(method, url, **kwargs)
            resp.raise_for_status()
            return resp
        except httpx.RequestError as e:
            log.error(f"method: {method}, url: {url}, 网络请求失败: {e}")
            raise AuthError(-1, f"网络错误: {e}") from e
        except httpx.HTTPStatusError as e:
            log.error(f"method: {method}, url: {url}, HTTP 错误: {e}")
            raise AuthError(e.response.status_code, f"HTTP 错误: {e}") from e

    def get_state(self) -> str:
        """获取 OAuth2 state 值"""
        url = urljoin(self.backend_oauth_url, "/115cloud/state")
        respjson = self._do_request("GET", url).json()
        state = self._get_key(respjson, "state")
        assert state, "获取 state 失败"
        return state

    def get_authorize_url(self, state: str = "random123") -> str:
        """获取授权 URL

        Args:
            state: 可选的 state 参数，默认为"random123"，如果未提供则自动获取

        Returns:
            授权 URL 字符串, 在控制台中会打印该链接供用户访问授权

        """
        self._state = self.get_state() if not self.client_secret else state
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "state": self._state,
        }
        return f"{API.Oauth2.AUTHORIZE}?{urlencode(params)}"

    def fetch_token(self, code: str) -> dict:
        """根据授权码获取 token

        用户访问授权 URL 并授权后，会得到一个 code 参数值，使用该值调用此方法获取 token。

        Args:
            code: 授权码，从重定向 URL 的 code 参数中获取

        Returns:
            包含 access_token, refresh_token 等信息的响应数据字典

        """
        if not self.client_secret:
            # 使用后端代理获取 token
            data = {
                "client_id": self.client_id,
                "code": code,
                "redirect_uri": self.redirect_uri,
                "grant_type": "authorization_code",
                "state": self._state,
            }
            url = urljoin(self.backend_oauth_url, "/115cloud/open/authCodeToToken")
            resp = self._do_request("POST", url, json=data)
        else:
            # 直接使用客户端凭据获取 token
            data = {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "code": code,
                "redirect_uri": self.redirect_uri,
                "grant_type": "authorization_code",
            }
            resp = self._do_request("POST", API.Oauth2.TOKEN, data=data)
        return resp.json()

    def _refresh_token_if_needed(self) -> str:
        """检测并自动刷新 token"""
        if self.is_token_valid:
            return self.access_token

        if not self.refresh_token:
            # 无 refresh_token，则重新授权
            print("请重新授权访问以下链接：")
            print(self.get_authorize_url())
            code = input("请输入授权完成后返回的 code 参数值: ").strip()
            respjson = self.fetch_token(code)
        else:
            # 一定要注意用data还是json
            respjson = self._do_request("POST", API.Oauth2.REFRESH, data={"refresh_token": self.refresh_token}).json()
        self._update_token(respjson)
        return self.access_token

    def get_access_token(self) -> str:
        """获取有效的 access_token, 如果过期则自动刷新

        Returns:
            有效的 access_token 字符串
        """
        access_token = self._refresh_token_if_needed()
        if not access_token:
            raise AuthError(40140116, "无法获取有效的 access_token")
        return access_token
