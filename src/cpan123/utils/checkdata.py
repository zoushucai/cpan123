from typing import BinaryIO, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, field_validator


class JsonInput(BaseModel):
    method: str
    url: str
    data: Optional[Dict] = None
    params: Optional[Dict] = None
    schema_: Optional[Dict] = None
    comment: Optional[str] = None
    response_schema: Optional[Dict] = None

    model_config = ConfigDict(extra="forbid")  # 禁止额外字段

    @field_validator("method")
    @classmethod
    def validate_method(cls, v: str) -> str:
        allowed = {"get", "post", "put", "delete"}
        v_lower = v.lower()
        if v_lower not in allowed:
            raise ValueError(f"method 必须是以下之一: {allowed}")
        return v_lower  # 统一返回小写形式


class BaseResponse(BaseModel):
    """
    基础响应类.
    """

    code: int = 0
    message: str = ""
    data: Optional[dict] = None
    x_traceID: Optional[str] = None


class DataResponse:
    response_data = None

    def __init__(self, response=None, code=0, message="", data=None):
        """
        服务器返回数据类.

        :param response: 服务器返回原 请求 数据
        :param code: 自定义响应值.
        :param message: 自定义消息.
        :param data: 自定义数据.
        """
        if response is None:
            self.response = None
            self.response_data = {
                "code": code,
                "message": message,
                "data": data,
                "x-traceID": "",
            }
            return
        else:
            self.response = response
            self.response_data = response.json()

    @property
    def data(self):
        """
        服务器返回数据段.
        :return: str
        """
        if isinstance(self.response_data, dict):
            return self.response_data.get("data")
        return None

    @property
    def x_traceID(self):
        """
        服务器记录值.
        :return: str
        """
        if isinstance(self.response_data, dict):
            return self.response_data.get("x-traceID")
        return None

    @property
    def message(self):
        """
        服务器返回消息.
        :return: str
        """
        if isinstance(self.response_data, dict):
            return self.response_data.get("message")
        return None

    @property
    def success(self):
        """
        是否成功
        :return: bool
        """
        if isinstance(self.response_data, dict):
            return self.response_data.get("code") == 0
        return False

    @property
    def code(self):
        if isinstance(self.response_data, dict):
            return self.response_data.get("code")
        return None

    @property
    def fileList(self):
        """
        服务器返回文件列表.
        :return: list
        """
        if isinstance(self.response_data, dict):
            data = self.response_data.get("data", None)
            if isinstance(data, dict):
                return data.get("fileList", None)
        return None

    @property
    def downloadUrl(self):
        """
        服务器返回下载链接.
        :return: str
        """
        if isinstance(self.response_data, dict):
            return self.response_data.get("data", {}).get("downloadUrl", None)
        return None

    def __repr__(self):
        """
        返回响应的字符串表示.
        :return: str
        """
        return (
            f"DataResponse(code={self.code}, message={self.message}, data={self.data})"
        )

    def __str__(self):
        """
        返回响应的字符串表示.
        :return: str
        """
        return (
            f"DataResponse(code={self.code}, message={self.message}, data={self.data})"
        )


class UploadInChunks:
    def __init__(
        self,
        fp: BinaryIO,
        length: int,
        idx: int,
        progress_ref: List[float],
        chunksize: int = 1 << 13,
    ) -> None:
        """
        初始化一个支持分块上传的文件读取器.

        Args:
            fp (BinaryIO): 文件对象(必须是以二进制方式打开的).
            length (int): 文件总大小(字节数).
            idx (int): 当前任务的索引,用于在 progress_ref 中更新进度.
            progress_ref (List[float]): 外部进度列表的引用.
            chunksize (int, optional): 每次读取的字节大小,默认 8192(8KB)
        """
        self.fp = fp
        self.idx = idx
        self.chunksize = chunksize
        self.totalsize = length
        self.readsofar = 0
        self.progress_ref = progress_ref

    def __iter__(self) -> "UploadInChunks":
        """
        实现迭代器接口.

        Returns:
            UploadInChunks: 迭代器本身.
        """
        return self

    def __next__(self) -> bytes:
        """
        迭代读取下一个数据块.

        Returns:
            bytes: 下一块文件数据.

        Raises:
            StopIteration: 当读取完毕时抛出.
        """
        if self.readsofar >= self.totalsize:
            raise StopIteration

        # 计算应该读取的大小
        read_len = min(self.chunksize, self.totalsize - self.readsofar)
        data: bytes = self.fp.read(read_len)

        if not data:
            raise StopIteration

        self.readsofar += len(data)
        self.progress_ref[self.idx] = self.readsofar * 100 / self.totalsize
        return data

    def __len__(self) -> int:
        """
        返回总字节数.

        Returns:
            int: 文件总大小.
        """
        return self.totalsize


if __name__ == "__main__":
    import json5

    with open("src/cpan123/apijson/file.json", "r", encoding="utf-8") as f:
        data = json5.load(f)

    for name, conf in data.items():
        try:
            validated = JsonInput.model_validate(conf)
            print(f"{name} ✅ 验证通过: {validated}")
        except Exception as e:
            print(f"{name} ❌ 验证失败: {e}")
