from __future__ import annotations

from typing import Any, List, Optional

from .utils.api import Auth
from .utils.baseapiclient import BaseApiClient, auto_args_call_api
from .utils.checkdata import DataResponse


class Oss(BaseApiClient):
    def __init__(self, auth: Optional[Auth] = None) -> None:
        super().__init__(filepath="oss", auth=auth)

    @auto_args_call_api("mkdir")
    def mkdir(
        self, name: str, parentID: str, type: int = 1, skip: bool = False
    ) -> DataResponse:  # type: ignore
        """创建目录

        Args:
            name (str): 目录名(注:不能重名)
            parentID (str): 父目录id,上传到根目录时为空
            type (int): 固定为 1,
            skip (bool): 是否跳过响应数据的模式校验
        """
        pass

    @auto_args_call_api()
    def create(
        self,
        parentFileID: str,
        filename: str,
        etag: str,
        size: float,
        type: int = 1,
        skip: bool = False,
    ) -> DataResponse:  # type: ignore
        """创建文件

        Args:
            parentFileID (str): 父目录id,上传到根目录时填写 空
            filename (str): 文件名要小于255个字符且不能包含以下任何字符:"\\/:*?|><. (注:不能重名)
            etag (str): 文件md5
            size (int): 文件大小,单位为 byte 字节
            type (int): 固定为 1
            skip (bool): 是否跳过响应数据的模式校验

        """
        pass

    @auto_args_call_api("get_upload_url")
    def get_upload_url(
        self, preuploadID: str, sliceNo: int, skip: bool = False
    ) -> DataResponse:  # type: ignore
        """获取上传地址&上传分片

        Args:
            preuploadID (str): 预上传ID
            sliceNo (int): 分片序号,从1开始自增
            skip (bool): 是否跳过响应数据的模式校验

        """
        pass

    @auto_args_call_api("upload_complete")
    def upload_complete(self, preuploadID: str, skip: bool = False) -> DataResponse:  # type: ignore
        """上传完毕

        Args:
            preuploadID (str): 预上传ID
            skip (bool): 是否跳过响应数据的模式校验
        """
        pass

    @auto_args_call_api("upload_async_result")
    def upload_async_result(self, preuploadID: str, skip: bool = False) -> DataResponse:  # type: ignore
        """异步轮询获取上传结果

        Args:
            preuploadID (str): 预上传ID
            skip (bool): 是否跳过响应数据的模式校验
        """
        pass

    @auto_args_call_api("copy")
    def copy(
        self,
        fileIDs: List[str],
        toParentFileID: str,
        sourceType: str,
        type: int,
        skip: bool = False,
    ) -> DataResponse:  # type: ignore
        """创建复制任务

        说明:图床复制任务创建(可创建的任务数:3,fileIDs 长度限制:100,当前一个任务处理完后将会继续处理下个任务)

        该接口将会复制云盘里的文件或目录对应的图片到对应图床目录,每次任务包含的图片总数限制 1000 张,图片格式:png, gif, jpeg, tiff, webp,jpg,tif,svg,bmp,图片大小限制:100M,文件夹层级限制:15层

        如果图床目录下存在相同 etag、size 的图片将会视为同一张图片,将覆盖原图片


        Args:
            fileIDs (List[str]): 文件id数组(string 数组)
            toParentFileID (str): 要移动到的图床目标文件夹id,移动到根目录时为空
            sourceType (str): 复制来源(1=云盘)
            type (int): 业务类型,固定为 1
            skip (bool): 是否跳过响应数据的模式校验
        """
        pass

    @auto_args_call_api("process")
    def process(self, taskID: str, skip: bool = False) -> DataResponse:  # type: ignore
        """获取复制任务详情

        说明:该接口将会获取图床复制任务执行情况

        Args:
            taskID (str): 复制任务ID
            skip (bool): 是否跳过响应数据的模式校验
        """
        pass

    @auto_args_call_api("fail")
    def fail(
        self, taskID: str, limit: int, page: int, skip: bool = False
    ) -> DataResponse:  # type: ignore
        """获取复制失败文件列表

        说明:查询图床复制任务失败文件列表(注:记录的是符合对应格式、大小的图片的复制失败原因)

        Args:
            taskID (str): 复制任务ID
            limit (int): 每页文件数量,最大不超过100
            page (int): 页码数
            skip (bool): 是否跳过响应数据的模式校验
        """
        if limit > 100:
            raise ValueError("❌ limit must be less than 100")
        pass

    @auto_args_call_api("move")
    def move(self, fileIDs: List[str], toParentFileID: str, skip: bool = False) -> None:
        """移动文件或目录

        Args:
            fileIDs (List[str]): 文件id数组(string 数组)
            toParentFileID (str): 要移动到的目标文件夹id,移动到根目录时填写 空
            skip (bool): 是否跳过响应数据的模式校验
        """
        pass

    @auto_args_call_api("delete")
    def delete(self, fileIDs: List[str]) -> None:
        """删除文件或目录

        Args:
            fileIDs (List[str]): 文件id数组,参数长度最大不超过 100
        """
        if len(fileIDs) > 100:
            raise ValueError("❌ fileIDs length must be less than 100")

    @auto_args_call_api()
    def detail(self, fileID: str) -> DataResponse | None:
        """获取文件或目录详情

        Args:
            fileID (str): 文件ID
        """
        pass

    @auto_args_call_api()
    def file_list(
        self,
        parentFileId: Optional[str] = "",
        limit: int = 20,
        startTime: Optional[int] = None,
        endTime: Optional[int] = None,
        lastFileId: Optional[str] = None,
        type: int = 1,
        skip: bool = False,
    ) -> DataResponse:  # type: ignore
        """获取图片列表

        Args:
            parentFileId (str): 父级目录Id, 默认为空表示筛选根目录下的文件
            limit (int): 每页文件数量,最大不超过100
            startTime (int, optional): 筛选开始时间(时间戳格式,例如 1730390400)
            endTime (int, optional): 筛选结束时间(时间戳格式,例如 1730390400)
            lastFileId (str, optional): 上翻页查询时需要填写
            type (int): 业务类型,固定为 1
            skip (bool): 是否跳过响应数据的模式校验
        """
        if limit > 100:
            raise ValueError("❌ imit must be less than 100")

    def list(self, *args: Any, **kwargs: Any) -> DataResponse:
        """获取图片列表

        等价与 self.file_list()

        Args:
            args (Any): 传入参数
            kwargs (Any): 传入参数
        """
        return self.file_list(*args, **kwargs)

    @auto_args_call_api()
    def offline_download(
        self,
        url: str,
        fileName: Optional[str] = None,
        businessDirID: Optional[str] = None,
        callBackUrl: Optional[str] = None,
        type: int = 1,
        skip: bool = False,
    ) -> DataResponse:  # type: ignore
        """离线下载

        Args:
            url (str): 下载资源地址(http/https)
            fileName (str, optional):  自定义文件名称 (需携带图片格式,支持格式:png, gif, jpeg, tiff, webp,jpg,tif,svg,bmp)
            businessDirID (str, optional): 选择下载到指定目录ID.  示例:10023. 注:不支持下载到根目录,默认下载到名为"来自:离线下载"的目录中
            callBackUrl (str, optional): 回调地址,当文件下载成功或者失败,均会通过回调地址通知
            type (int): 业务类型,固定为 1
            skip (bool): 是否跳过响应数据的模式校验
        """

    @auto_args_call_api()
    def offline_process(self, taskID: int, skip: bool = False) -> DataResponse:  # type: ignore
        """获取离线迁移任务

        说明:获取当前离线下载任务状态

        Args:
            taskID (int):离线下载任务ID
            skip (bool): 是否跳过响应数据的模式校验
        """
        pass
