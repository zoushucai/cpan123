import importlib.resources as pkg_resources
import sys
import warnings
from pathlib import Path
from typing import Any, Dict, Optional, Union

import json5
import requests
from jsonpath import jsonpath
from jsonschema import validate
from pydantic import Field, TypeAdapter, dataclasses

from .auth import Auth
from .checkdata import BaseResponse, DataResponse, JsonInput

BASE_URL = "https://open-api.123pan.com"
PLATFORM = "open_platform"
HEADERS = {
    # "Authorization": "Bearer " + self.auth.access_token,
    # "Content-Type": "application/json",
    "Platform": PLATFORM,
}


def _replace_values(obj: Any) -> Any:
    if isinstance(obj, dict):
        new_dict = {}
        for key, value in obj.items():
            # 替换可选值为 None
            if isinstance(value, str) and ": optional" in value:
                value = None
            elif isinstance(value, str) and ": required" in value:
                value = value.replace(": required", "")
            else:
                value = _replace_values(value)
            new_dict[key] = value
        return new_dict

    elif isinstance(obj, list):
        return [_replace_values(item) for item in obj]
    else:
        return obj


def get_api(filepath: str, *args: Any) -> dict:
    """
    获取 API.

    Args:
        filepath (str): API 所属分类,即 `apijson/***.json`下的文件名(不含后缀名)
        *args (Any): 预留的可选参数(当前未使用).

    Returns:
        dict, 该 API 的内容.
    """
    path = Path(filepath)
    # 如果没有后缀,则添加.json后缀
    if not Path(filepath).suffix:
        path = path.with_suffix(".json")

    # 如果是相对路径,则在当前目录下查找
    # 处理相对路径
    if not path.is_absolute():
        try:
            path = pkg_resources.files("cpan123.apijson").joinpath(str(path))
            path = Path(str(path))
        except ModuleNotFoundError:
            print("❌ 找不到模块 `cpan123.apijson`,请确认路径或依赖包正确")
            sys.exit(1)

    if not path.exists():
        print(f"❌ 文件不存在: {path}")
        sys.exit(1)

    # 读取并校验 JSON 文件
    with open(path, "r", encoding="utf-8") as file:
        try:
            data: dict = json5.load(file)
        except Exception as e:
            print(f"❌ JSON 解析失败: {path}\n错误: {e}")
            sys.exit(1)

    # # 对json文件进行验证
    # for name, conf in data.items():
    #     try:
    #         JsonInput.model_validate(conf)
    #     except Exception as e:
    #         print(f"❌ 校验失败: {name}\n内容: {conf}\n错误: {e}")
    #         sys.exit(1)
    list_adapter = TypeAdapter(Dict[str, JsonInput])
    list_adapter.validate_python(data)
    # 按参数索引嵌套数据
    for arg in args:
        try:
            data = data[arg]
        except KeyError:
            print(f"❌ 参数 `{arg}` 不存在于 API 数据中")
            sys.exit(1)
    return _replace_values(data)


@dataclasses.dataclass
class Api:
    """
    用于请求的 Api 类
    """

    method: str
    url: str
    data: Optional[dict] = Field(default_factory=dict)
    params: Optional[dict] = Field(default_factory=dict)
    response_schema: Optional[dict] = Field(default_factory=dict)
    schema_: Optional[dict] = Field(default_factory=dict)
    comment: str = ""
    auth: Auth = Field(default_factory=Auth)
    headers: dict = Field(default_factory=dict)
    files: Optional[dict] = Field(default_factory=dict)
    skip: bool = Field(default=False)

    def __post_init__(self) -> None:
        """
        初始化 Api 对象
        """
        # 获取请求方法
        self.method = self.method.upper()
        self.data = self.data or None
        self.params = self.params or None
        self.response_schema = self.response_schema or None
        self.schema_ = self.schema_ or None
        self.auth = self.auth or Auth()
        self.headers = self.headers or HEADERS.copy()
        self.files = self.files or None

    def update_auth(self, **kwargs) -> "Api":
        for key in ["access_token", "clientID", "clientSecret"]:
            if key in kwargs:
                setattr(self.auth, key, kwargs.pop(key))
        return self

    def _update_attr(self, attr: str, **kwargs) -> "Api":
        if "skip" in kwargs:
            self.skip = kwargs.pop("skip")
        value = {k: v for k, v in kwargs.items() if v is not None}
        setattr(self, attr, value)
        return self

    def update_data(self, **kwargs) -> "Api":
        return self._update_attr("data", **kwargs)

    def update_params(self, **kwargs) -> "Api":
        return self._update_attr("params", **kwargs)

    def update_files(self, arg) -> "Api":
        self.files = arg
        return self

    def update_method(self, method: str) -> "Api":
        self.method = method.upper()
        return self

    def update_url(self, url: str) -> "Api":
        self.url = url
        return self

    def update_headers(self, **kwargs) -> "Api":
        self.headers = kwargs
        return self

    def _prepare_request(self) -> dict:
        """
        准备请求参数
        """

        headers = self.headers.copy()
        if not self.files:
            headers["Content-Type"] = "application/json"
        headers["Authorization"] = f"Bearer {self.auth.access_token}"

        full_url = (
            self.url
            if self.url.startswith("http")
            else f"{BASE_URL.rstrip('/')}/{self.url.lstrip('/')}"
        )
        config = {
            "method": self.method,
            "url": full_url,
            "params": self.params,
            "data": self.data,
            "files": self.files,
            "headers": headers,
        }

        config = {k: v for k, v in config.items() if v is not None}
        return config

    def request(
        self, byte: bool = False
    ) -> Union[int, str, dict, bytes, None, DataResponse]:
        """
        发送请求并返回结果

        Args:
            byte (bool): 是否返回字节流,默认为 False
        """
        # 处理请求参数
        config: dict = self._prepare_request()
        # print("---" * 10)
        # print(f"🔍 请求参数: {config}")
        response = requests.request(**config)

        response.raise_for_status()
        if byte:
            return response.text

        if self.skip:
            # 如果不需要验证响应数据的 schema_,则直接返回
            return DataResponse(response)

        if self.schema_:
            res_json: dict = response.json()
            BaseResponse.model_validate(res_json)
            if res_json.get("data"):
                validate(
                    instance=res_json["data"],
                    schema=self.schema_,
                )
                return DataResponse(response)
            else:
                print(f"❌ 响应数据: {response.text}")
                print(f"❌ 响应数据: {res_json}")
                if res_json.get("code") == 401:
                    print(f"❌ {res_json.get('message')}")
                    sys.exit(1)
                raise ValueError("❌ 利用 schema_ 校验失败, 没有 data 字段")

        if self.response_schema:
            check = self.validate_response_schema(response, self.response_schema)
            if check:
                return DataResponse(response)
            else:
                raise ValueError("❌ 利用 response_schema 校验失败")

        return DataResponse(response)

    @property
    def result(self) -> DataResponse:
        res = self.request()
        if isinstance(res, DataResponse):
            return res
        else:
            raise ValueError("❌ 响应数据解析失败")

    @staticmethod
    def validate_response_schema(response: requests.Response, schema_: dict) -> bool:
        if not schema_:
            return True

        try:
            response.raise_for_status()
            res_json = response.json()
            BaseResponse.model_validate(res_json)
        except Exception as e:
            print(f"❌ 响应数据解析失败: {response.text}\n错误: {e}")
            return False

        type_mapping = {
            "string": str,
            "number": (int, float),
            "boolean": bool,
            "bool": bool,
            "object": dict,
            "array": list,
        }

        errors = []

        for k, rule in schema_.items():
            expected_type = type_mapping.get(rule["type"])
            actual = jsonpath(res_json, f"$..{k}")
            if not actual:
                errors.append(f"Key '{k}' 不存在于响应中")
                continue
            if expected_type and not isinstance(actual[0], expected_type):
                errors.append(
                    f"Key '{k}' 的类型为 {type(actual[0]).__name__}, 应为 {rule['type']}"
                )

        if errors:
            for error in errors:
                print(f"❌ {error}")
            warnings.warn(f"⚠️ 校验失败响应: {res_json}", stacklevel=2)
            return False

        return True


__all__ = [
    "get_api",
    "Api",
    "Auth",
]
