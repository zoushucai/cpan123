from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .encode import detect_and_convert_to_md5


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


class Share123FileModel(BaseModel):
    model_config = ConfigDict(extra="ignore")  # ✅ 忽略所有未定义字段
    etag: str
    size: str
    path: str

    @model_validator(mode="after")
    def normalize_path(self) -> "Share123FileModel":
        """确保etag 是32位的md5值, 且 size 必须小于10G"""
        if len(self.etag) != 32:
            ## 检查是否为 base62 编码的 md5 值. 尝试对其进行解码
            etag = detect_and_convert_to_md5(self.etag)
            if len(etag) == 32:
                self.etag = etag
            else:
                raise AuthError(1001, "etag 不是有效的32位MD5值或可解码的base62/base64编码")
        if int(self.size) >= 10 * 1024 * 1024 * 1024:
            raise AuthError(1002, "文件大小超过10GB限制")
        return self
