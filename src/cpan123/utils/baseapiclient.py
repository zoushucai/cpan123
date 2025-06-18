import contextvars
import inspect
import sys
from functools import wraps
from typing import Any, Callable, Optional, Union

from tenacity import RetryCallState, retry, stop_after_attempt, wait_random

from .api import Api, Auth, get_api
from .checkdata import DataResponse
from .core import FieldParser

# 通用装饰器:自动收集参数并调用 API

caller_var = contextvars.ContextVar("caller_name", default="unknown")


def auto_args_call_api(arg: Union[Callable, str, None] = None) -> Callable:
    def decorator(func: Callable, api_name: Optional[str] = None) -> Callable:
        @wraps(func)
        def wrapper(self, *args, **kwargs) -> DataResponse:
            func(self, *args, **kwargs)
            bound_args = inspect.signature(func).bind(self, *args, **kwargs)
            bound_args.apply_defaults()
            arguments = dict(bound_args.arguments)
            arguments["auth"] = getattr(self, "auth", None)
            arguments.pop("self")
            caller_var.set(func.__name__)
            return self._call_api(api_name or func.__name__, **arguments)

        return wrapper

    if callable(arg):
        return decorator(arg)
    return lambda func: decorator(func, api_name=arg)


class BaseApiClient:
    def __init__(self, filepath: str, auth: Optional[Auth] = None) -> None:
        self.auth = auth
        self.filepath = filepath
        self.API: dict[str, Any] = get_api(self.filepath)

    @retry(
        stop=stop_after_attempt(10),
        wait=wait_random(min=1, max=5),
        before_sleep=lambda state: BaseApiClient.print_retry_info(state),
    )
    def _call_api(self, mmkey: str, **data: Any) -> DataResponse:
        """统一的 API 调用方式

        Args:
            mmkey (str): API 的名称, 来源于json文件的 mmkey, 防止和其他的常用词冲突,命名为 mmkey
            **data (Any): 请求的参数, 这些参数会覆盖 API 配置中的默认值

        """
        api = self.API[mmkey]
        parsed = FieldParser.parse_dict(api)
        checked_data = FieldParser.validate_and_fill_input(parsed, data)
        api_instance = Api(**checked_data)
        method = api_instance.method.upper()
        residual_params = {
            k: v
            for k, v in data.items()
            if v is not None
            and k not in (api_instance.params or {})
            and k not in (api_instance.data or {})
            and k not in ["url", "URL", "skip", "auth"]
        }
        if residual_params:
            print(f"❌ 发现多余的参数: {residual_params.keys()}, 请检查 API 配置")
            sys.exit(1)
        if method in ["GET", "POST", "PUT", "DELETE"]:
            return DataResponse(api_instance.result)
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
        # 获取上下文中的调用者名
        fn_name = caller_var.get()
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
