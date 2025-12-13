from .Auth import Auth
from .Directlink import Directlink
from .Downloader import Downloader
from .File import File
from .File2 import File2
from .FileList import FileList
from .Offline import Offline
from .Share import Share
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

        self.userinfo = self.user.userinfo
        assert self.userinfo is not None, "用户未授权,请先完成授权流程"
        self.file = File(self.auth, self.userinfo)
        self.file2 = File2(self.auth, self.userinfo)
        self.uploader = Uploader(self.auth, self.userinfo)
        self.downloader = Downloader(self.auth, self.userinfo)

        log.info(f"已登录用户: {self.userinfo.username} (ID: {self.userinfo.userid}, ISVIP: {self.userinfo.isvip})")
        self.filelist = FileList(self.auth, self.userinfo)
        self.share = Share(self.auth, self.userinfo)
        self.offline = Offline(self.auth, self.userinfo)
        self.directlink = Directlink(self.auth, self.userinfo)
