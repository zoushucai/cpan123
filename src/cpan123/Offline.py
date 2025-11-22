from typing import Optional

from pydantic import validate_call

from .Auth import Auth
from .model.Base import UserInfoModel
from .utils import API


class Offline:
    def __init__(self, auth: Auth, userinfo: UserInfoModel | None = None) -> None:
        """初始化

        Args:
            auth (Auth): 已授权的 Auth 实例

        """
        self.auth = auth
        self.userinfo = userinfo

    @validate_call
    def download(
        self,
        url: str,
        fileName: Optional[str] = None,
        dirID: Optional[int] = None,
        callBackUrl: Optional[str] = None,
    ) -> dict:
        """
        创建离线下载任务


        Args:
            url: 下载链接
            fileName: 自定义文件名称 (需携带图片格式,支持格式:png, gif, jpeg, tiff, webp,jpg,tif,svg,bmp)
            dirID: 选择下载到指定目录ID.  示例:10023, 注:不支持下载到根目录,默认会下载到名为"来自:离线下载"的目录中
            callBackUrl: 回调地址,当文件下载成功或者失败,均会通过回调地址通知.
        """
        data = {
            "url": url,
            "fileName": fileName,
            "dirID": dirID,
            "callBackUrl": callBackUrl,
        }
        return self.auth.request_json("POST", API.OfflinePath.DOWNLOAD, json=data)

    @validate_call
    def process(self, taskID: int) -> dict:
        """
        获取离线下载进度

        Args:
            taskID: 离线下载任务ID
        """
        params = {
            "taskID": taskID,
        }
        return self.auth.request_json("GET", API.OfflinePath.DOWNLOAD_PROCESS, params=params)
