from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any, Optional

from pydantic import Field, conlist

from .utils.api import Auth
from .utils.baseapiclient import BaseApiClient, auto_args_call_api
from .utils.checkdata import DataResponse
from .utils.md5 import calculate_md5


class File(BaseApiClient):
    def __init__(self, auth: Optional[Auth] = None) -> None:
        super().__init__(filepath="file", auth=auth)

    @auto_args_call_api("create")
    def create(
        self,
        parentFileID: int,
        filename: str,
        etag: str = Field(default="", max_length=32),
        size: int = Field(default=0, gt=0),
        duplicate: int = 1,
        containDir: bool = False,
        skip: bool = False,
    ) -> DataResponse:  # type: ignore
        """
        创建文件上传任务.

        - 文件名不能全部是空格
        - 开发者上传单文件大小限制10GB

        Args:
            parentFileID (int): 父目录id,上传到根目录时填写 0
            filename (str): 文件名要小于255个字符且不能包含一些特殊字符(不建议重名)
            etag (str): 文件的md5值, 如果不传入,则自动计算
            size (int): 文件大小, 单位字节
            duplicate (int): 当有相同文件名时,文件处理策略(1保留两者,新文件名将自动添加后缀,2覆盖原文件)
            containDir (bool):上传文件是否包含路径,默认fasle
            skip (bool): 是否跳过响应数据的模式校验
        """

    @auto_args_call_api()
    def get_upload_url(
        self,
        preuploadID: str,
        sliceNo: int = Field(ge=1),
        skip: bool = False,
    ) -> DataResponse:  # type: ignore
        """获取文件上传地址.

        Args:
            preuploadID (str): 预上传ID
            sliceNo (int): 分片序号,从1开始自增
            skip (bool): 是否跳过响应数据的模式校验
        """

    @auto_args_call_api()
    def list_upload_parts(
        self,
        preuploadID: str,
        skip: bool = False,
    ) -> DataResponse:  # type: ignore
        """获取文件上传分片列表.

        Args:
            preuploadID (str): 预备上传ID
            skip (bool): 是否跳过响应数据的模式校验
        """
        # 获取 API

    @auto_args_call_api()
    def upload_complete(
        self,
        preuploadID: str,
        skip: bool = False,
    ) -> DataResponse:  # type: ignore
        """文件上传完成后请求

        Args:
            preuploadID (str): 预上传ID
            skip (bool): 是否跳过响应数据的模式校验
        """

    @auto_args_call_api()
    def upload_async_result(
        self,
        preuploadID: str,
        skip: bool = False,
    ) -> DataResponse:  # type: ignore
        """异步轮询获取上传结果

        Args:
            preuploadID (str): 预上传ID
            skip (bool): 是否跳过响应数据的模式校验
        """

    @auto_args_call_api()
    def mkdir(
        self,
        name: str,
        parentID: int,
        skip: bool = False,
    ) -> DataResponse:  # type: ignore
        """创建目录
        Args:
            name (str): 目录名称
            parentID (int): 父目录ID
            skip (bool): 是否跳过响应数据的模式校验
        """

    @auto_args_call_api()
    def name(
        self,
        fileId: int,
        fileName: str,
        skip: bool = False,
    ) -> DataResponse:  # type: ignore
        """单个文件重命名

        Args:
            fileId (int): 文件ID
            fileName (str): 新文件名
            skip (bool): 是否跳过响应数据的模式校验
        """

    @auto_args_call_api()
    def rename(
        self,
        renameList: list[str],
        skip: bool = False,
    ) -> DataResponse:  # type: ignore
        """批量重命名文件,最多支持同时30个文件重命名

        Args:
            renameList (list): 重命名列表,格式为 [14705301|测试文件重命名","14705306|测试文件重命名.mp4"]
            skip (bool): 是否跳过响应数据的模式校验
        """

    @auto_args_call_api()
    def trash(
        self,
        fileIDs: Annotated[list[int], conlist(int, max_length=100)],
        skip: bool = False,
    ) -> DataResponse:  # type: ignore
        """删除的文件,会放入回收站中

        Args:
            fileIDs (list[int]): 文件id数组,一次性最大不能超过 100 个文件
            skip (bool): 是否跳过响应数据的模式校验
        """

    @auto_args_call_api()
    def recover(
        self,
        fileIDs: Annotated[list[int], conlist(int, max_length=100)],
        skip: bool = False,
    ) -> DataResponse:  # type: ignore
        """将回收站的文件恢复至删除前的位置

        Args:
            fileIDs (list): 文件id数组,一次性最大不能超过 100 个文件
            skip (bool): 是否跳过响应数据的模式校验
        """

    @auto_args_call_api()
    def delete(
        self,
        fileIDs: Annotated[list[int], conlist(int, max_length=100)],
        skip: bool = False,
    ) -> DataResponse:  # type: ignore
        """彻底删除文件前,文件必须要在回收站中,否则无法删除

        Args:
            fileIDs (list): 文件id数组,参数长度最大不超过 100
            skip (bool): 是否跳过响应数据的模式校验
        """

    @auto_args_call_api()
    def detail(
        self,
        fileID: int,
        skip: bool = False,
    ) -> DataResponse:  # type: ignore
        """获取单个文件详情

        Args:
            fileID (int): 文件ID
            skip (bool): 是否跳过响应数据的模式校验
        """

    @auto_args_call_api()
    def infos(
        self,
        fileIds: list[int],
        skip: bool = False,
    ) -> DataResponse:  # type: ignore
        """获取多个文件详情

        Args:
            fileIds (list): 文件ID列表
            skip (bool): 是否跳过响应数据的模式校验
        """

    @auto_args_call_api("list_v2")
    def list_v2(
        self,
        parentFileId: int,
        limit: int = Field(default=100, gt=0, le=100),
        searchData: Optional[str] = None,
        searchMode: Optional[int] = 0,
        lastFileId: Optional[int] = None,
        skip: bool = False,
    ) -> DataResponse:  # type: ignore
        """获取文件列表(V2版本, v1弃用)

        Args:
            parentFileId (int): 文件夹ID,根目录传 0
            limit (int): 每页文件数量,最大不超过100
            searchData (str, optional):搜索关键字将无视文件夹ID参数. 将会进行全局查找
            searchMode (int, optional): 搜索模式,0:模糊搜索,1:精确搜索,默认为0
            lastFileId (int, optional): 翻页查询时需要填写
            skip (bool): 是否跳过响应数据的模式校验
        """
        # 这里的函数体根本不会执行, 因为被装饰器给劫持了, 返回的结果是装饰器的返回值,所以对参数进行校验无效
        # 如果要对参数进行校验,需要 Field 等参数校验方法
        # 默认已开启函数参数校验

    @auto_args_call_api("list_v1")
    def list_v1(
        self,
        parentFileId: int = 0,
        page: int = 1,
        limit: int = Field(default=100, gt=0, le=100),
        orderBy: str = "file_id",
        orderDirection: str = "asc",
        trashed: Optional[bool] = True,
        searchData: Optional[str] = "",
        skip: bool = False,
    ) -> DataResponse:  # type: ignore
        pass

    def list(self, *args: Any, **kwargs: Any) -> DataResponse:
        """获取文件列表(V1版本, v2弃用)

        具体参考 list_v2的用法,这个只是一个别名, 因为list和python中的list冲突了(为了尽力保证和url的末端一致性)

        Args:
            args (Any): 传入参数
            kwargs (Any): 传入参数
        """
        # 获取 API
        return self.list_v2(*args, **kwargs)

    @auto_args_call_api()
    def move(
        self,
        fileIDs: list[int],
        toParentFileID: int = 0,
        skip: bool = False,
    ) -> DataResponse:  # type: ignore
        """批量移动文件,单级最多支持100个

        Args:
            fileIDs (list[int]): 文件id数组
            toParentFileID (int): 要移动到的目标文件夹id,移动到根目录时填写 0
            skip (bool): 是否跳过响应数据的模式校验
        """

    @auto_args_call_api()
    def download_info(
        self,
        fileId: int,
        skip: bool = False,
    ) -> DataResponse:  # type: ignore
        """获取文件下载地址

        Args:
            fileId (int): 文件ID
            skip (bool): 是否跳过响应数据的模式校验
        """
        # 获取 API
        # return self._call_api("download_info", fileID=fileID)

    def calculate_md5(self, file_path: Path | str) -> str:
        """计算文件的 MD5 值

        Args:
            file_path (Path | str): 文件路径,可以是 Path 对象或字符串

        Returns:
            str: 文件的 MD5 值

        Raises:
            AssertionError: 文件不存在或路径不是文件或文件大小为0

        """
        return calculate_md5(file_path)


if __name__ == "__main__":
    file = File()

    print(file.list_v2(0, 10, "data").data)
