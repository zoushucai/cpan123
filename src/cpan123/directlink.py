from __future__ import annotations

from typing import Optional

from .utils.api import Auth
from .utils.baseapiclient import BaseApiClient, auto_args_call_api
from .utils.checkdata import DataResponse


class DirectLink(BaseApiClient):
    def __init__(self, auth: Optional[Auth] = None) -> None:
        super().__init__(filepath="directlink", auth=auth)

    @auto_args_call_api()
    def enable(
        self,
        fileID: int,
        skip: bool = False,
    ) -> DataResponse:  # type: ignore
        """启用直链

        Args:
            fileID (int): 启用直链空间的文件夹的fileID
            skip (bool): 是否跳过响应数据的模式校验
        """

    @auto_args_call_api("url")
    def url(
        self,
        fileID: int,
        skip: bool = False,
    ) -> DataResponse:  # type: ignore
        """获取直链 URL

        Args:
            fileID (int): 需要获取直链链接的文件的fileID
            skip (bool): 是否跳过响应数据的模式校验
        """

    @auto_args_call_api("log")
    def log(
        self,
        pageNum: int,
        pageSize: int,
        startTime: int,
        endTime: int,
        skip: bool = False,
    ) -> DataResponse:  # type: ignore
        """获取直链日志

        Args:
            pageNum (int): 页数
            pageSize (int): 分页大小
            startTime (int): 开始时间
            endTime (int): 结束时间
            skip (bool): 是否跳过响应数据的模式校验
        """

    @auto_args_call_api("disable")
    def disable(
        self,
        fileID: int,
        skip: bool = False,
    ) -> DataResponse:  # type: ignore
        """禁用直链

        Args:
            fileID (int): 禁用直链空间的文件夹的fileID
            skip (bool): 是否跳过响应数据的模式校验
        """
