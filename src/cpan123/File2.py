from typing import Union

from pydantic import Field, validate_call

from .Auth import Auth
from .model.Base import UserInfoModel
from .utils import API


class File2:
    """123 文件上传 V2 接口封装类"""

    def __init__(self, auth: Auth, userinfo: UserInfoModel | None = None) -> None:
        """初始化

        Args:
            auth (Auth): 已授权的 Auth 实例
        """
        self.auth = auth
        self.userinfo = userinfo

    @validate_call
    def create(
        self,
        parentFileID: int,
        filename: str,
        etag: str = Field(default="", max_length=32),
        size: int = Field(default=0, gt=0),
        *,
        duplicate: int = 1,
        containDir: bool = False,
    ) -> dict:
        """
        创建文件上传任务.

        - 文件名不能全部是空格
        - 开发者上传单文件大小限制10GB
        - 文件名要小于256个字符且不能包含以下任何字符: `"\\/:*?|><`

        Args:
            parentFileID: 父目录id,上传到根目录时填写 0
            filename: 文件名要小于255个字符且不能包含一些特殊字符(不建议重名)
            etag: 文件的md5值, 如果不传入,则自动计算
            size: 文件大小, 单位字节
            duplicate: 当有相同文件名时,文件处理策略(1保留两者,新文件名将自动添加后缀,2覆盖原文件)
            containDir: 上传文件是否包含路径,默认false

        Returns:
            创建上传任务的响应数据
        """
        data = {
            "parentFileID": parentFileID,
            "filename": filename,
            "etag": etag,
            "size": size,
            "duplicate": duplicate,
            "containDir": containDir,
        }
        return self.auth.request_json("POST", API.File2Path.CREATE, json=data)

    @validate_call
    def slice(
        self,
        preuploadID: Union[int, str],
        sliceNo: int,
        sliceMD5: str,
        slice: bytes,
        upload_server: str,
    ) -> dict:
        """上传文件分片.

        Args:
            preuploadID:  预上传ID（可以是字符串或整数）
            sliceNo: 分片序号，从1开始自增
            sliceMD5: 当前分片md5
            slice: 分片二进制流
            upload_server: 上传服务器地址（从创建文件接口返回的 servers 中获取）

        Returns:
            上传分片的响应数据
        """
        data = {
            "preuploadID": str(preuploadID),  # 确保转换为字符串
            "sliceNo": sliceNo,
            "sliceMD5": sliceMD5,
        }

        files = {
            "slice": ("slice", slice, "application/octet-stream"),
        }

        url = f"{upload_server}/upload/v2/file/slice"
        return self.auth.request_json("POST", url, data=data, files=files)

    @validate_call
    def upload_complete(self, preuploadID: Union[int, str]) -> dict:
        """完成文件上传.

        Args:
            preuploadID: 预上传ID（可以是字符串或整数）
        """
        data = {
            "preuploadID": str(preuploadID),  # 确保转换为字符串
        }
        return self.auth.request_json("POST", API.File2Path.UPLOAD_COMPLETE, json=data)

    @validate_call
    def domain(self) -> dict:
        """获取上传域名."""
        return self.auth.request_json("GET", API.File2Path.DOMAIN)

    @validate_call
    def single_create(
        self,
        parentFileID: int,
        filename: str,
        upload_server: str,
        etag: str = Field(default="", max_length=32),
        size: int = Field(default=0, gt=0),
        file: bytes = Field(default=b""),
        duplicate: int = 1,
        containDir: bool = False,
    ) -> dict:  # type: ignore
        """单步上传

        - 文件名要小于256个字符且不能包含以下任何字符
        - 文件名不能全部是空格
        - 此接口限制开发者上传单文件大小为1GB
        - 上传域名是获取上传域名接口响应中的域名
        - 此接口用于实现小文件单步上传一次HTTP请求交互即可完成上传

        Args:
            parentFileID: 父目录id,上传到根目录时填写 0
            filename: 文件名要小于255个字符且不能包含一些特殊字符(不建议重名)
            etag: 文件的md5值, 如果不传入,则自动计算
            size: 文件大小, 单位字节
            file: 文件二进制流
            duplicate: 当有相同文件名时,文件处理策略(1保留两者,新文件名将自动添加后缀,2覆盖原文件)
            containDir: 上传文件是否包含路径,默认false
            upload_server: 上传服务器地址（从获取上传域名接口返回）

        Returns:
            单步上传的响应数据

        """
        data = {
            "parentFileID": parentFileID,
            "filename": filename,
            "etag": etag,
            "size": size,
            "duplicate": duplicate,
            "containDir": containDir,
        }

        files = {
            "file": (filename, file, "application/octet-stream"),
        }

        # 如果提供了上传服务器地址，使用完整URL；否则使用默认路径
        url = f"{upload_server}/upload/v2/file/single/create"
        return self.auth.request_json("POST", url, data=data, files=files)
