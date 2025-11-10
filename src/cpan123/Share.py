from __future__ import annotations

from typing import Literal, Optional

from pydantic import Field, validate_call

from .Auth import Auth
from .utils import API


class Share:
    def __init__(self, auth: Auth) -> None:
        self.auth = auth

    @validate_call
    def share_create(
        self,
        shareName: str,
        shareExpire: Literal[0, 1, 7, 30],
        fileIDList: str,
        sharePwd: Optional[str] = None,
        trafficSwitch: Literal[1, 2, 3, 4] = 1,
        trafficLimitSwitch: Literal[1, 2] = 1,
        trafficLimit: int = 10000**2,
    ) -> dict:
        """
        创建免费分享链接

        Args:
            shareName: 分享链接名称,链接名要小于35个字符且不能包含特殊字符
            shareExpire: 分享链接有效期天数,该值为枚举, 固定只能填写:1、7、30、0, 填写0时代表永久分享
            fileIDList: 分享文件ID列表,以逗号分割,最大只支持拼接100个文件ID,示例:1,2,3
            sharePwd: 设置分享链接提取码
            trafficSwitch:分享提取流量包

                1 全部关闭
                2 打开游客免登录提取
                3 打开超流量用户提取
                4 全部开启

            trafficLimitSwitch: 分享提取流量包流量限制开关.   1 关闭限制, 2 打开限制
            trafficLimit: 分享提取流量包限制流量, 单位：字节

        """
        if fileIDList.count(",") + 1 > 100:
            raise ValueError("fileIDList 参数最多只支持100个文件ID,请修改后重试")

        data = {
            "shareName": shareName,
            "shareExpire": shareExpire,
            "fileIDList": fileIDList,
            "sharePwd": sharePwd,
            "trafficSwitch": trafficSwitch,
            "trafficLimitSwitch": trafficLimitSwitch,
            "trafficLimit": trafficLimit,
        }
        return self.auth.request_json("POST", API.SharePath.CREATE, json=data)

    @validate_call
    def share_list(
        self,
        limit: int = Field(gt=0, le=100),
        lastShareId: int = 0,
    ) -> dict:
        """
        获取分享链接列表

        Args:
            limit: 每页分享链接数量,最大不超过100
            lastShareId: 翻页查询时需要填写

        Returns:
            获取分享链接列表的响应数据

        """
        params = {
            "limit": limit,
            "lastShareId": lastShareId,
        }
        return self.auth.request_json("GET", API.SharePath.LIST, params=params)

    @validate_call
    def share_change(
        self,
        shareIdList: list[int],
        trafficSwitch: int = 1,
        trafficLimitSwitch: int = 1,
        trafficLimit: int = 10000**2,
    ) -> dict:
        """修改分享链接

        Args:
            shareIdList:  分享链接ID列表,数组长度最大为100
            trafficSwitch: 分享提取流量包
                - 1 全部关闭
                - 2 打开游客免登录提取
                - 3 打开超流量用户提取
                - 4 全部开启
            trafficLimitSwitch: 分享提取流量包流量限制开关.   1 关闭限制, 2 打开限制
            trafficLimit: 分享提取流量包限制流量, 单位：字节

        Returns:
            修改分享链接的响应数据
        """

        data = {
            "shareIdList": shareIdList,
            "trafficSwitch": trafficSwitch,
            "trafficLimitSwitch": trafficLimitSwitch,
            "trafficLimit": trafficLimit,
        }
        return self.auth.request_json("PUT", API.SharePath.INFO, json=data)

    @validate_call
    def payment_create(
        self,
        shareName: str = Field(max_length=35),
        fileIDList: str = Field(max_length=10000),
        payAmount: int = Field(gt=0, le=99),
        resourceDesc: str = Field(max_length=100, default=""),
        isReward: int = Field(default=0, ge=0, le=10),
    ) -> dict:
        """
        创建付费分享链接

        Args:
            shareName (str): 分享链接名称,链接名要小于35个字符且不能包含特殊字符
            fileIDList (str): 分享文件ID列表,以逗号分割,最大只支持拼接100个文件ID,示例:1,2,3
            payAmount (int): 请输入整数|最小金额1元|最大金额99元
            isReward (int): 是否打赏, 0 否, 1 是, 默认 0
            resourceDesc (str): 资源描述

        Returns:
            创建付费分享链接的响应数据

        """
        data = {
            "shareName": shareName,
            "fileIDList": fileIDList,
            "payAmount": payAmount,
            "isReward": isReward,
            "resourceDesc": resourceDesc,
        }
        return self.auth.request_json("POST", API.SharePath.CONTENT_PAYMENT_CREATE, json=data)

    @validate_call
    def payment_list(
        self,
        limit: int = Field(gt=0, le=100),
        lastShareId: int = 0,
    ) -> dict:
        """
        获取付费分享链接列表

        Args:
            limit (int): 每页分享链接数量,最大不超过100
            lastShareId (int): 翻页查询时需要填写

        Returns:
            获取付费分享链接列表的响应数据
        """
        params = {
            "limit": limit,
            "lastShareId": lastShareId,
        }
        return self.auth.request_json("GET", API.SharePath.CONTENT_PAYMENT_LIST, params=params)

    @validate_call
    def payment_change(
        self,
        shareIdList: list[int],
        trafficSwitch: int = 1,
        trafficLimitSwitch: int = 1,
        trafficLimit: int = 10000**2,
    ) -> dict:
        """修改付费分享链接

        Args:
            shareIdList: 分享链接ID列表，数组长度最大为100
            trafficSwitch:  分享提取流量包
                        1 全部关闭
                        2 打开游客免登录提取
                        3 打开超流量用户提取
                        4 全部开启
            trafficLimitSwitch: 分享提取流量包流量限制开关.   1 关闭限制, 2 打开限制
            trafficLimit: 分享提取流量包限制流量, 单位：字节

        Returns:
            修改付费分享链接的响应数据
        """

        data = {
            "shareIdList": shareIdList,
            "trafficSwitch": trafficSwitch,
            "trafficLimitSwitch": trafficLimitSwitch,
            "trafficLimit": trafficLimit,
        }
        return self.auth.request_json("PUT", API.SharePath.CONTENT_PAYMENT_INFO, json=data)
