"""
v1版本, 不含上传文件等操作, 因为v2版本已经支持上传文件等操作
"""

import sys
from typing import Optional

from pydantic import Field, validate_call

from .Auth import Auth
from .model.Base import UserInfoModel
from .utils import API, log


class File:
    """123 文件上传 V1 接口封装类"""

    def __init__(self, auth: Auth, userinfo: UserInfoModel | None = None) -> None:
        """初始化 File 客户端

        Args:
            auth (Auth): 已授权的 Auth 实例
        """
        self.auth = auth
        self.userinfo = userinfo

    @validate_call
    def mkdir(self, name: str, parentID: int, verbose: bool = True) -> dict:
        """创建目录
        Args:
            name (str): 目录名称
            parentID (int): 父目录ID
        """
        data = {
            "name": name,
            "parentID": parentID,
        }
        return self.auth.request_json("POST", API.FilePath.MKDIR, json=data, verbose=verbose)

    @validate_call
    def name(
        self,
        fileId: int,
        fileName: str,
    ) -> dict:
        """单个文件重命名

        Args:
            fileId (int): 文件ID
            fileName (str): 新文件名

        """
        data = {
            "fileID": fileId,
            "fileName": fileName,
        }
        return self.auth.request_json("PUT", API.FilePath.NAME, json=data)

    @validate_call
    def rename(
        self,
        renameList: list[str],
    ) -> dict:
        """批量重命名文件,最多支持同时30个文件重命名

        Args:
            renameList (list): 重命名列表,格式为 [14705301|测试文件重命名","14705306|测试文件重命名.mp4"]

        """
        if len(renameList) > 30:
            log.error("renameList 参数长度最大不超过 30,请修改后重试")
            sys.exit(1)
        # 检查格式
        for item in renameList:
            if "|" not in item or len(item.split("|")) != 2:
                log.error(f"renameList 参数格式错误: {item}, 正确格式为 fileID|新文件名,请修改后重试")
                sys.exit(1)
        return self.auth.request_json("POST", API.FilePath.RENAME, json={"renameList": renameList})

    @validate_call
    def trash(
        self,
        fileIDs: list[int],
    ) -> dict:
        """删除的文件,会放入回收站中

        Args:
            fileIDs (list[int]): 文件id数组,一次性最大不能超过 100 个文件

        """
        if len(fileIDs) > 100:
            log.error("fileIDs 参数长度最大不超过 100,请修改后重试")
            sys.exit(1)
        return self.auth.request_json("POST", API.FilePath.TRASH, json={"fileIDs": fileIDs})

    @validate_call
    def delete(
        self,
        fileIDs: list[int],
    ) -> dict:
        """彻底删除文件前,文件必须要在回收站中,否则无法删除

        Args:
            fileIDs (list): 文件id数组,参数长度最大不超过 100

        """
        if len(fileIDs) > 100:
            log.error("fileIDs 参数长度最大不超过 100,请修改后重试")
            sys.exit(1)
        return self.auth.request_json("POST", API.FilePath.DELETE, json={"fileIDs": fileIDs})

    @validate_call
    def recover(
        self,
        fileIDs: list[int],
    ) -> dict:
        """将回收站的文件恢复至删除前的位置

        Args:
            fileIDs (list): 文件id数组,一次性最大不能超过 100 个文件

        """
        if len(fileIDs) > 100:
            log.error("fileIDs 参数长度最大不超过 100,请修改后重试")
            sys.exit(1)
        data = {
            "fileIDs": fileIDs,
        }
        return self.auth.request_json("POST", API.FilePath.RECOVER, json=data)

    @validate_call
    def recover_by_path(
        self,
        fileIDs: list[int],
        parentFileID: int = 0,
    ) -> dict:
        """将回收站的文件恢复至删除前的位置

        Args:
            fileIDs (list): 文件id数组,一次性最大不能超过 100 个文件

        """
        if len(fileIDs) > 100:
            log.error("fileIDs 参数长度最大不超过 100,请修改后重试")
            sys.exit(1)
        data = {
            "fileIDs": fileIDs,
            "parentFileID": parentFileID,
        }
        return self.auth.request_json("POST", API.FilePath.RECOVER_BY_PATH, json=data)

    @validate_call
    def detail(
        self,
        fileID: int,
    ) -> dict:
        """获取单个文件详情

        Args:
            fileID (int): 文件ID

        """
        return self.auth.request_json("GET", API.FilePath.DETAIL, params={"fileID": fileID})

    @validate_call
    def infos(
        self,
        fileIds: list[int],
    ) -> dict:
        """获取多个文件详情

        Args:
            fileIds (list): 文件ID列表

        """
        return self.auth.request_json("POST", API.FilePath.INFOS, json={"fileIds": fileIds})

    @validate_call
    def list_v2(
        self,
        parentFileId: int,
        limit: int = 100,
        searchData: Optional[str] = None,
        searchMode: Optional[int] = 0,
        lastFileId: Optional[int] = None,
        isTrashed: bool = False,
    ) -> dict:
        """获取文件列表(V2版本, v1弃用)

        此接口查询结果包含回收站的文件，需自行根据字段trashed判断处理

        Args:
            parentFileId (int): 文件夹ID,根目录传 0
            limit (int): 每页文件数量,最大不超过100
            searchData (str, optional):搜索关键字将无视文件夹ID参数. 将会进行全局查找
            searchMode (int, optional): 搜索模式,0:模糊搜索,1:精确搜索,默认为0
            lastFileId (int, optional): 翻页查询时需要填写
            isTrashed (bool): 是否包含回收站文件,默认不包含 (官方是包含的)

        """
        # 如果要对参数进行校验,需要 Field 等参数校验方法
        # 默认已开启函数参数校验
        # 也可以在函数体中进行参数校验了, 不能参与计算
        # print(self.list_v2.__name__)
        # print(self.list_v2.__doc__)
        if limit > 100 and limit < 0:
            log.error("limit 参数最大值为 100,请修改后重试")
            sys.exit(1)
        params = {
            "parentFileId": parentFileId,
            "limit": limit,
            "searchData": searchData,
            "searchMode": searchMode,
            "lastFileId": lastFileId,
        }
        resp = self.auth.request_json("GET", API.FilePath.LIST_V2, params=params)
        # 不能要回收站的文件
        if isTrashed:
            return resp

        try:
            resp["data"]["fileList"] = [file for file in resp["data"]["fileList"] if file.get("trashed") == 0]
            return resp
        except Exception as e:
            log.error(f"过滤回收站文件时出错: {e}")
            return resp

    @validate_call
    def list_v1(
        self,
        parentFileId: int = 0,
        page: int = 1,
        limit: int = Field(default=100, gt=0, le=100),
        orderBy: str = "file_id",
        orderDirection: str = "asc",
        trashed: Optional[bool] = True,
        searchData: Optional[str] = "",
    ) -> dict:
        """获取文件列表(V1版本, v2弃用)

        具体参考 list_v2的用法,这个只是一个别名, 因为list和python中的list冲突了(为了尽力保证和url的末端一致性)

        Args:
            parentFileId (int): 文件夹ID,根目录传 0
            page (int): 页码,从 1 开始
            limit (int): 每页文件数量,最大不超过100
            orderBy (str): 排序字段,file_id(默认),filename,size,created_at,updated_at
            orderDirection (str): 排序方式,asc(默认),desc
            trashed (bool, optional): 是否包含回收站文件,默认包含
            searchData (str, optional): 搜索关键字将无视文件夹ID参数. 将会进行全局查找

        """
        if limit > 100 and limit < 0:
            log.error("limit 参数最大值为 100,请修改后重试")
            sys.exit(1)
        params = {
            "parentFileId": parentFileId,
            "page": page,
            "limit": limit,
            "orderBy": orderBy,
            "orderDirection": orderDirection,
            "trashed": trashed,
            "searchData": searchData,
        }
        return self.auth.request_json("GET", API.FilePath.LIST, params=params)

    @validate_call
    def move(
        self,
        fileIDs: list[int],
        toParentFileID: int = 0,
    ) -> dict:
        """批量移动文件,单级最多支持100个

        Args:
            fileIDs: 文件id数组
            toParentFileID: 要移动到的目标文件夹id,移动到根目录时填写 0

        """
        if len(fileIDs) > 100:
            log.error("fileIDs 参数长度最大不超过 100,请修改后重试")
            sys.exit(1)
        data = {
            "fileIDs": fileIDs,
            "toParentFileID": toParentFileID,
        }
        return self.auth.request_json("POST", API.FilePath.MOVE, json=data)

    @validate_call
    def download_info(
        self,
        fileId: int,
    ) -> dict:
        """获取文件下载地址

        Args:
            fileId (int): 文件ID

        """
        return self.auth.request_json("GET", API.FilePath.DOWNLOAD_INFO, params={"fileId": fileId})
