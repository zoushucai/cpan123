from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class UserInfoModel(BaseModel):
    """统一的用户模型, 过滤掉其他不必要的字段"""

    model_config = ConfigDict(extra="ignore")  # ✅ 忽略所有未定义字段

    username: str
    userid: str
    isvip: bool | None = None
    viptype: int | None = None


class AuthError(Exception):
    """123 平台统一异常"""

    def __init__(self, code: int, message: str, detail: dict | None = None):
        self.code = code
        self.message = message
        self.detail = detail or {}
        super().__init__(f"[{code}] {message}")


class BaseResponse(BaseModel):
    """统一响应模型"""

    model_config = ConfigDict(extra="allow")  # ✅ 保留所有未定义字段

    code: int
    message: str
    data: dict[str, Any] | list[Any] | None  # data 字段可以是 dict、list 或 None
    x_traceID: str = Field(alias="x-traceID")

    @model_validator(mode="after")
    def check_code(self) -> "BaseResponse":
        """验证 code 字段，失败时抛出 AuthError"""
        if self.code != 0:  # code 不为0时表示失败
            raise AuthError(self.code, self.message)
        return self
