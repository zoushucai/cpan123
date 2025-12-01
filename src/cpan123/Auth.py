from typing import Any
from urllib.parse import urljoin

import httpx

from .authtype.Jwt import Jwt
from .model.Base import BaseResponse
from .utils.Constants import API
from .utils.Logger import log


class Auth(Jwt):
    """带自动 Bearer Token 的授权请求类

    该类继承自 Jwt, 自动在请求中添加 Bearer Token 进行授权。

    """

    def request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        """带授权头的请求

        根据不同的要求, 添加一些通用的请求头。

        Args:
            method: HTTP 方法，如 "GET", "POST" 等
            url: 请求的完整 URL 或相对路径
            **kwargs: 传递给 httpx 请求的其他参数，如 headers, params, json 等

        Returns:
            httpx.Response: HTTP 响应对象
        """
        url = url if url.startswith("http") else urljoin(API.API_BASE, url)

        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {self.get_access_token()}"
        headers["Platform"] = "open_platform"
        kwargs["headers"] = headers

        # 对 kwargs 进行处理, 如果有params, data, json等, 删除None值
        for key in ["params", "data", "json"]:
            if key in kwargs and isinstance(kwargs[key], dict):
                kwargs[key] = {k: v for k, v in kwargs[key].items() if v is not None}

        return self._do_request(method, url, **kwargs)

    def request_json(self, method: str, url: str, **kwargs: Any) -> dict:
        """带授权头的请求，并解析为统一响应模型

        Args:
            method: HTTP 方法，如 "GET", "POST" 等
            url: 请求的完整 URL 或相对路径
            kwargs: 传递给 httpx 请求的其他参数，如 headers, params, json 等

        Returns:
            解析后的响应数据，符合统一响应模型
        """
        try:
            resp = self.request(method, url, **kwargs)
            resp.raise_for_status()
            respjson = resp.json()
        except Exception as e:
            log.error(f"请求失败: {e}")
            log.error(f"请求方法: {method}, URL: {url}")
            log.error(f"原始响应: {resp.text if 'resp' in locals() else '无响应'}")
            raise ValueError("请求过程中发生错误，请检查日志以获取详细信息。") from e
        if 429 == respjson.get("code"):
            # '操作频繁，请稍后再试' (防止打印大量日志)
            return respjson

        try:
            parsed = BaseResponse.model_validate(respjson)
            return parsed.model_dump()
        except Exception as e:
            log.error(f"解析响应 JSON 失败: {e}")
            log.error(f"请求方法: {method}, URL: {url}")
            log.error(f"原始响应: {respjson}")
            return respjson
