from .Auth import Auth
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

    def get_user_info(self) -> dict:
        """获取用户信息, 通过调用 GET /open/user/info 接口

        Returns:
            包含用户信息
        """
        resp = self.auth.request_json("GET", API.UserPath.USER_INFO)
        return resp
