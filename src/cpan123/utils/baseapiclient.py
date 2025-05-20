from __future__ import annotations

import inspect
from functools import wraps
from typing import Any, Callable, Optional

from pydantic import validate_call
from tenacity import RetryCallState, retry, stop_after_attempt, wait_random

from .api import Api, Auth, get_api
from .checkdata import DataResponse

# 通用装饰器:自动收集参数并调用 API


def auto_args_call_api(api_name: Optional[str] = None) -> Callable:
    def decorator(func: Callable) -> Callable:
        @validate_call
        @wraps(func)
        def wrapper(self, *args, **kwargs) -> DataResponse:
            # 绑定参数,自动填充默认值
            bound_args = inspect.signature(func).bind(self, *args, **kwargs)
            bound_args.apply_defaults()
            arguments = dict(bound_args.arguments)
            arguments.pop("self")

            # 自动调用内部 API
            return self._call_api(api_name or func.__name__, **arguments)

        return wrapper

    return decorator


class BaseApiClient:
    def __init__(self, filepath: str, auth: Optional[Auth] = None) -> None:
        self.auth = auth
        self.filepath = filepath
        self.API: dict[str, Any] = get_api(self.filepath)

    def _merge_with_data(self, template: Any, data: dict) -> dict | None:
        """
        根据 template 的 key,从 data 中提取对应的值并更新 template.
        不会新增 key,只更新已有的 key.
        """
        if not template:
            return None
        if not isinstance(template, dict):
            return template

        result = {}
        for k, v in template.items():
            if k in data:
                result[k] = data[k]
            else:
                result[k] = v
        return result if result else None

    @retry(
        stop=stop_after_attempt(10),
        wait=wait_random(min=1, max=5),
        before_sleep=lambda state: BaseApiClient.print_retry_info(state),
    )
    def _call_api(self, key: str, **data: Any) -> DataResponse:
        """统一的 API 调用方式

        Args:
            key (str): API 的名称, 来源于json文件的 key
            **data (Any): 请求的参数, 这些参数会覆盖 API 配置中的默认值

        """
        api = self.API[key]
        BINARY_KEYS = ["files"]

        for k in BINARY_KEYS:
            api.pop(k, None)

        url = data.pop("url", None)
        files = data.get("files", None)
        skip = data.get("skip", False)

        if self.auth:
            # 过滤掉 api 中的 auth和 skip
            for k in ["skip", "auth"]:
                api.pop(k, None)
            api_instance = Api(auth=self.auth, skip=skip, **api)
        else:
            # 过滤掉 api 中的 skip
            for k in ["skip"]:
                api.pop(k, None)
            api_instance = Api(skip=skip, **api)

        method = api_instance.method.upper()

        data1 = self._merge_with_data(api_instance.data, data)
        params = self._merge_with_data(api_instance.params, data)

        # # ###剩余的参数
        residual_params = {
            k: v
            for k, v in data.items()
            if v is not None
            and k not in (data1 or {})
            and k not in (params or {})
            and k not in (api_instance.params or {})
            and k not in (api_instance.data or {})
            and k not in BINARY_KEYS
            and k not in ["url", "URL", "skip"]
        }
        # print(f"residual_params: {residual_params}")
        if residual_params:
            raise ValueError(f"❌ 发现多余的参数: {residual_params}, 请检查 API 配置")

        if method in ["GET", "POST", "PUT", "DELETE"]:
            if data1:
                api_instance.update_data(**data1)
            if params:
                api_instance.update_params(**params)
            if files:
                api_instance.update_files(files)
            if url:
                api_instance.update_url(url)
            return api_instance.result  # type: ignore
        else:
            print("----" * 10)
            print("❌ 无法识别的请求类型,请检查 API 配置")
            print(f"❌ method: {method}")
            print(f"❌ params: {api.get('params')}")
            print(f"❌ data: {api.get('data')}")
            print("----" * 10)
            raise ValueError("❌ 无法识别的请求类型,请检查 API 配置")

    @staticmethod
    def print_retry_info(retry_state: RetryCallState):
        fn_name = retry_state.fn.__name__ if retry_state.fn is not None else "Unknown"
        args = retry_state.args
        kwargs = retry_state.kwargs
        if kwargs and "files" in kwargs:
            kwargs.pop("files", None)

        exception = (
            retry_state.outcome.exception() if retry_state.outcome is not None else None
        )
        print("---" * 10)
        print("⚠️ 调用失败,准备重试...")
        print(f"🔁 函数: {fn_name}")
        print(f"📥 参数: args={args}")
        print(f"📥 参数: kwargs={kwargs}")
        print(f"💥 异常: {exception}")
        if retry_state.next_action is not None and hasattr(
            retry_state.next_action, "sleep"
        ):
            print(f"⏳ 等待 {retry_state.next_action.sleep:.2f} 秒后重试...\n")
        else:
            print("⏳ 等待时间未知,无法获取 next_action.sleep\n")
        print("---" * 10)
