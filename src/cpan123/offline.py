from __future__ import annotations

from typing import Optional

from .utils.api import Auth
from .utils.baseapiclient import BaseApiClient, auto_args_call_api
from .utils.checkdata import DataResponse


class Offline(BaseApiClient):
    def __init__(self, auth: Optional[Auth] = None) -> None:
        super().__init__(filepath="offline", auth=auth)

    @auto_args_call_api()
    def download(
        self,
        url: str,
        fileName: Optional[str] = None,
        dirID: Optional[int] = None,
        callBackUrl: Optional[str] = None,
        skip: bool = False,
    ) -> DataResponse:  # type: ignore
        """
        创建离线下载任务


        Args:
            url (str): 下载链接
            fileName (str, optional): 自定义文件名称 (需携带图片格式,支持格式:png, gif, jpeg, tiff, webp,jpg,tif,svg,bmp)
            dirID (int, optional): 选择下载到指定目录ID.  示例:10023, 注:不支持下载到根目录,默认会下载到名为"来自:离线下载"的目录中
            callBackUrl (str, optional): 回调地址,当文件下载成功或者失败,均会通过回调地址通知.
            skip (bool): 是否跳过响应数据的模式校验
        """

    @auto_args_call_api()
    def process(
        self,
        taskID: int,
        skip: bool = False,
    ) -> DataResponse:  # type: ignore
        """
        获取离线下载进度

        Args:
            taskID (int): 离线下载任务ID
            skip (bool): 是否跳过响应数据的模式校验
        """
