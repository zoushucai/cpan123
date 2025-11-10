from .Auth import Auth
from .Downloader import Downloader
from .File2 import File2
from .Uploader import Uploader
from .User import User
from .utils.Constants import API
from .utils.Logger import log


class Pan123OpenAPI:
    """
    123开放接口客户端
    包含用户信息与上传等功能
    """

    def __init__(self, envpath: str | None = None, verbose: bool = False):
        self.API = API
        self.log = log
        self.auth = Auth(envpath=envpath, verbose=verbose)
        self.user = User(self.auth)
        self.file2 = File2(self.auth)
        self.uploader = Uploader(self.auth)
        self.downloader = Downloader(self.auth)
