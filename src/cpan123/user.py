from __future__ import annotations

from typing import Optional

from .utils.api import Auth
from .utils.baseapiclient import BaseApiClient, auto_args_call_api
from .utils.checkdata import DataResponse


class User(BaseApiClient):
    def __init__(self, auth: Optional[Auth] = None) -> None:
        super().__init__(filepath="user", auth=auth)

    @auto_args_call_api()
    def info(self, skip=False) -> DataResponse:  # type: ignore
        """
        获取用户信息
        """
