from pydantic import validate_call

from .Auth import Auth
from .model.Base import UserInfoModel
from .utils import API


class Directlink:
    """123 直链接口封装类"""

    def __init__(self, auth: Auth, userinfo: UserInfoModel | None = None) -> None:
        """初始化 Directlink 客户端

        Args:
            auth (Auth): 已授权的 Auth 实例
        """
        self.auth = auth
        self.userinfo = userinfo

    @validate_call
    def enable(self, fileID: int) -> dict:
        """启用直链

        Args:
            fileID (int): 启用直链空间的文件夹的fileID

        Returns:
            成功启用直链空间的文件夹的名称
        """
        data = {
            "fileID": fileID,
        }
        return self.auth.request_json("POST", API.DirectlinkPath.ENABLE, json=data)

    # 获取直链链接
    @validate_call
    def url(self, fileID: int) -> dict:
        """获取直链 URL

        Args:
            fileID (int): 需要获取直链链接的文件的fileID

        Returns:
            包含直链 URL 的响应数据
        """
        params = {
            "fileID": fileID,
        }
        return self.auth.request_json("GET", API.DirectlinkPath.URL, params=params)

    # 禁用直链空间
    @validate_call
    def disable(self, fileID: int) -> dict:
        """禁用直链

        Args:
            fileID (int): 需要禁用直链空间的文件夹的fileID

        Returns:
            成功禁用直链空间的文件夹的名称
        """
        data = {
            "fileID": fileID,
        }
        return self.auth.request_json("POST", API.DirectlinkPath.DISABLE, json=data)

    # 直链缓存刷新
    @validate_call
    def refresh(self, url: str) -> dict:
        """直链缓存刷新

        Args:
            url (str): 需要刷新的直链URL

        Returns:
            刷新结果
        """

        return self.auth.request_json("POST", API.DirectlinkPath.CACHE_REFRESH)

    # 获取直链离线日志
    @validate_call
    def log(
        self,
        pageNum: int,
        pageSize: int,
        startHour: str,
        endHour: str,
    ) -> dict:
        """获取直链日志

        Args:
            pageNum (int): 页数，从1开始
            pageSize (int): 分页大小
            startHour (str): 开始时间，格式：2025010115
            endHour (str): 结束时间，格式：2025010116

        Returns:
            直链离线日志数据
        """
        params = {
            "pageNum": pageNum,
            "pageSize": pageSize,
            "startHour": startHour,
            "endHour": endHour,
        }
        return self.auth.request_json("GET", API.DirectlinkPath.LOG, params=params)

    # 获取直链流量日志
    @validate_call
    def log_traffic(
        self,
        pageNum: int,
        pageSize: int,
        startTime: str,
        endTime: str,
    ) -> dict:
        """获取直链流量日志

        Args:
            pageNum (int): 页数，从1开始
            pageSize (int): 分页大小
            startTime (str): 开始时间，格式：2025-01-01 00:00:00
            endTime (str): 结束时间，格式：2025-01-01 23:59:59

        Returns:
            直链流量日志数据
        """
        params = {
            "pageNum": pageNum,
            "pageSize": pageSize,
            "startTime": startTime,
            "endTime": endTime,
        }
        return self.auth.request_json("GET", API.DirectlinkPath.LOG_TRAFFIC, params=params)

    # 开启关闭ip黑名单
    @validate_call
    def ip_blacklist_switch(
        self,
        Status: int,
    ) -> dict:
        """开启关闭ip黑名单

        Args:
            Status (int): 状态：2禁用 1启用

        Returns:
            操作结果
        """
        data = {
            "Status": Status,
        }
        return self.auth.request_json("POST", API.DirectlinkPath.IP_BLACKLIST_SWITCH, json=data)

    # 更新ip黑名单列表
    @validate_call
    def ip_blacklist_update(
        self,
        IpList: list[str],
    ) -> dict:
        """更新ip黑名单列表

        Args:
            IPList (list): ip黑名单列表

        Returns:
            操作结果
        """
        data = {
            "IpList": IpList,
        }
        return self.auth.request_json("POST", API.DirectlinkPath.IP_BLACKLIST_UPDATE, json=data)

    # 获取开发者功能IP配置黑名单
    @validate_call
    def ip_blacklist_list(self) -> dict:
        """获取开发者功能IP配置黑名单

        Returns:
            IP黑名单列表
        """
        return self.auth.request_json("GET", API.DirectlinkPath.IP_BLACKLIST_LIST)
