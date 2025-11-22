from .Auth import Auth
from .model.Base import UserInfoModel
from .utils.Constants import API


class User:
    """
    用户信息接口客户端
    用于获取用户空间与 VIP 信息
    """

    def __init__(self, auth: Auth):
        """初始化

        Args:
            auth (Auth): 已授权的 Auth 实例

        """
        self.auth = auth
        self._user_resp_cache = None
        self.userinfo: UserInfoModel = self._fetch_user_info()

    def get_user_info(self) -> dict:
        """获取用户信息, 通过调用 GET /open/user/info 接口

        Returns:
            包含用户信息
        """
        if self._user_resp_cache is not None:
            return self._user_resp_cache

        resp = self.auth.request_json("GET", API.UserPath.USER_INFO)

        self._user_resp_cache = resp
        return resp

    def _fetch_user_info(self) -> UserInfoModel:
        """获取并缓存用户信息

        Returns:
            UserInfoModel: 用户信息模型

        Example Response:
            {'code': 0, 'message': 'ok', 'data': {'uid': 16666, 'nickname': '16666', .....,  'vip': True,  'vipInfo': [{'vipLevel': 1, 'vipLabel': 'VIP', 'startTime': '2024-06-14 15:52:05', 'endTime': '2029-03-23 23:59:00'}, {'vipLevel': 3, 'vipLabel': '长期VIP', 'startTime': '2025-05-15 01:25:05', 'endTime': '长期有效'}], 'developerInfo': None}}
        """
        try:
            resp = self.get_user_info()
        except Exception as e:
            raise ValueError("无法获取用户信息") from e

        try:
            data = resp.get("data", {})
            username = data.get("nickname")
            userid = str(data.get("uid"))
            isvip = data.get("vip")
            viptype = data.get("vipInfo")[0]["vipLevel"] if data.get("vipInfo") else None

            user_info = UserInfoModel(
                username=username,
                userid=userid,
                isvip=isvip,
                viptype=viptype,
            )
            return user_info
        except Exception as e:
            print(f"获取用户信息失败: {e}")
            print(f"原始响应: {resp}")
            raise ValueError(f"解析用户信息失败: {e}") from e
