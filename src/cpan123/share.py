from __future__ import annotations

from typing import Annotated, Any, Literal, Optional

from pydantic import Field, conlist

from .utils.api import Auth
from .utils.baseapiclient import BaseApiClient, auto_args_call_api
from .utils.checkdata import DataResponse


class Share(BaseApiClient):
    def __init__(self, auth: Optional[Auth] = None) -> None:
        super().__init__(filepath="share", auth=auth)

    @auto_args_call_api()
    def create_payment(
        self,
        shareName: str = Field(max_length=35),
        fileIDList: str = Field(max_length=10000),
        payAmount: int = Field(gt=0, le=99),
        resourceDesc: str = Field(max_length=100, default=""),
        isReward: int = Field(default=0, ge=0, le=10),
        skip: bool = False,
    ) -> DataResponse:  # type: ignore
        """
        创建付费分享链接

        Args:
            shareName (str): 分享链接名称,链接名要小于35个字符且不能包含特殊字符
            fileIDList (str): 分享文件ID列表,以逗号分割,最大只支持拼接100个文件ID,示例:1,2,3
            payAmount (int): 请输入整数|最小金额1元|最大金额99元
            isReward (int): 是否打赏, 0 否, 1 是, 默认 0
            resourceDesc (str): 资源描述
            skip (bool): 是否跳过响应数据的模式校验
        """

    @auto_args_call_api()
    def create_free(
        self,
        shareName: str,
        shareExpire: Literal[0, 1, 7, 30],
        fileIDList: Annotated[str, Field(max_length=10000)],
        sharePwd: Optional[str] = None,
        trafficSwitch: Optional[Literal[1, 2]] = None,
        trafficLimitSwitch: Optional[Literal[1, 2]] = None,
        trafficLimit: Optional[int] = Field(default=1000, ge=0),
        skip: bool = False,
    ) -> DataResponse:  # type: ignore
        """
        创建免费分享链接

        Args:
            shareName (str): 分享链接名称,链接名要小于35个字符且不能包含特殊字符
            shareExpire (float): 分享链接有效期天数,该值为枚举, 固定只能填写:1、7、30、0, 填写0时代表永久分享
            fileIDList (str): 分享文件ID列表,以逗号分割,最大只支持拼接100个文件ID,示例:1,2,3
            sharePwd (str): 设置分享链接提取码
            trafficSwitch (int): 免登录流量包开关, 1 关闭免登录流量包, 2 打开免登录流量包
            trafficLimitSwitch (int): 选填	免登录流量限制开关 1 关闭限制 2 打开限制
            trafficLimit (int): 免登陆限制流量 (单位:字节)
            skip (bool): 是否跳过响应数据的模式校验
        """

    def create(self, *args: Any, **kwargs: Any) -> DataResponse:
        """创建分享链接, create_free 方法的别名 ,本质就是调用 create_free 方法(为了尽力保证和url的末端一致性)

        Args:
            args (Any): 传入参数
            kwargs (Any): 传入参数
        """
        return self.create_free(*args, **kwargs)

    @auto_args_call_api()
    def change_share(
        self,
        shareIdList: Annotated[list[int], conlist(int, max_length=100)],
        trafficSwitch: Optional[Literal[1, 2]] = None,
        trafficLimitSwitch: Optional[Literal[1, 2]] = None,
        trafficLimit: Optional[int] = Field(default=1000, ge=0),
        skip: bool = False,
    ) -> DataResponse:  # type: ignore
        """修改分享链接

        Args:
            shareIdList (int): 分享链接ID列表,数组长度最大为100
            trafficSwitch (Optional[str], optional): 免登录流量包开关 1 关闭免登录流量包, 2 打开免登录流量包
            trafficLimitSwitch (Optional[str], optional): 免登录流量限制开关 1 关闭限制 2 打开限制
            trafficLimit (Optional[float], optional): 免登陆限制流量 (单位:字节)
            skip (bool): 是否跳过响应数据的模式校验, 原因在于没有返回值
        """

    def info(self, *args: Any, **kwargs: Any) -> DataResponse:
        """修改分享链接, change_share 方法的别名 (为了尽力保证和url的末端一致性)

        Args:
            args (Any): 传入参数
            kwargs (Any): 传入参数
        """
        return self.change_share(*args, **kwargs)

    @auto_args_call_api()
    def get_share(
        self,
        limit: int = Field(gt=0, le=100),
        lastShareId: int = 0,
        skip: bool = False,
    ) -> DataResponse:  # type: ignore
        """
        获取分享链接详情

        Args:
            limit (int): 每页分享链接数量,最大不超过100
            lastShareId (int): 翻页查询时需要填写
            skip (bool): 是否跳过响应数据的模式校验
        """

    def list(self, *args: Any, **kwargs: Any) -> DataResponse:
        """获取分享链接详情, get_share 方法的别名 (为了尽力保证和url的末端一致性)

        Args:
            args (Any): 传入参数
            kwargs (Any): 传入参数
        """
        return self.get_share(*args, **kwargs)
