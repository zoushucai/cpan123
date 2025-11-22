## 有关授权的
AUTH_BASE = "https://open-api.123pan.com"
API_BASE = "https://open-api.123pan.com"


class API:
    """123 接口路径和方法统一管理"""

    AUTH_BASE = AUTH_BASE
    API_BASE = API_BASE

    class Oauth2:
        # 不过123,只有一个直接获取令牌的接口(采用的是JWT授权模式)
        # 下面的是 oauth2 的标准接口路径,仅作保留(现在只对企业版开放)
        AUTHORIZE = AUTH_BASE + "/api/v1/access_token"  # 授权接口
        TOKEN = AUTH_BASE + "/api/v1/access_token"  # 利用授权码换取访问令牌
        REFRESH = AUTH_BASE + "/api/v1/access_token"  # 刷新访问令牌

    class JWT:
        TOKEN = AUTH_BASE + "/api/v1/access_token"  # 获取访问令牌

    # class FilePath:
    #     # --------- 文件上传下载相关接口 ----------
    #     UPLOAD_TOKEN = API_BASE + "/open/upload/get_token"
    #     UPLOAD_INIT = API_BASE + "/open/upload/init"
    #     UPLOAD_RESUME = API_BASE + "/open/upload/resume"

    #     # --------- 文件夹相关接口 ----------
    #     FOLDER_ADD = API_BASE + "/open/folder/add"
    #     FOLDER_INFO = API_BASE + "/open/folder/get_info"

    #     # --------- 文件相关接口 ----------
    #     UFILE_FILES = API_BASE + "/open/ufile/files"
    #     UFILE_SEARCH = API_BASE + "/open/ufile/search"
    #     UFILE_COPY = API_BASE + "/open/ufile/copy"
    #     UFILE_MOVE = API_BASE + "/open/ufile/move"
    #     UFILE_DOWNURL = API_BASE + "/open/ufile/downurl"
    #     UFILE_UPDATE = API_BASE + "/open/ufile/update"
    #     UFILE_DELETE = API_BASE + "/open/ufile/delete"

    #     # --------- 回收站相关接口 ----------
    #     RB_LIST = API_BASE + "/open/rb/list"
    #     RB_REVERT = API_BASE + "/open/rb/revert"
    #     RB_DELETE = API_BASE + "/open/rb/del"

    class UserPath:
        USER_INFO = API_BASE + "/api/v1/user/info"

    class File2Path:
        CREATE = API_BASE + "/upload/v2/file/create"
        # SLICE = API_BASE + "/upload/v2/file/slice"
        UPLOAD_COMPLETE = API_BASE + "/upload/v2/file/upload_complete"
        DOMAIN = API_BASE + "/upload/v2/file/domain"
        # SINGLE_CREATE = API_BASE + "/upload/v2/file/single/create"

    class FilePath:
        """文件相关接口 V1 版本(不含上传有关的接口, 因为上传接口在File2Path中)"""

        # POST   域名 + /upload/v1/file/mkdir
        MKDIR = API_BASE + "/upload/v1/file/mkdir"
        # PUT 域名 + /api/v1/file/name
        NAME = API_BASE + "/api/v1/file/name"

        #  POST 域名 + /api/v1/file/rename
        RENAME = API_BASE + "/api/v1/file/rename"

        #  POST 域名 + /api/v1/file/trash
        TRASH = API_BASE + "/api/v1/file/trash"

        # POST 域名 + /api/v1/file/delete
        DELETE = API_BASE + "/api/v1/file/delete"

        # POST 域名 + /api/v1/file/recover
        RECOVER = API_BASE + "/api/v1/file/recover"

        # POST 域名 + /api/v1/file/recover/by_path
        RECOVER_BY_PATH = API_BASE + "/api/v1/file/recover/by_path"

        # GET 域名 + /api/v1/file/detail
        DETAIL = API_BASE + "/api/v1/file/detail"

        # POST 域名 + /api/v1/file/infos
        INFOS = API_BASE + "/api/v1/file/infos"
        #  GET 域名 + /api/v2/file/list
        LIST_V2 = API_BASE + "/api/v2/file/list"

        #  GET 域名 + /api/v1/file/list
        LIST = API_BASE + "/api/v1/file/list"

        # POST 域名 + /api/v1/file/move
        MOVE = API_BASE + "/api/v1/file/move"

        # GET 域名 + /api/v1/file/download_info
        DOWNLOAD_INFO = API_BASE + "/api/v1/file/download_info"

    class SharePath:
        #  POST 域名 + /api/v1/share/create
        CREATE = API_BASE + "/api/v1/share/create"

        # GET 域名 + /api/v1/share/list
        LIST = API_BASE + "/api/v1/share/list"

        # PUT 域名 + /api/v1/share/list/info
        INFO = API_BASE + "/api/v1/share/list/info"

        # POST 域名 + /api/v1/share/content-payment/create
        CONTENT_PAYMENT_CREATE = API_BASE + "/api/v1/share/content-payment/create"
        # GET 域名 + /api/v1/share/payment/list
        CONTENT_PAYMENT_LIST = API_BASE + "/api/v1/share/payment/list"
        #  PUT 域名 + /api/v1/share/list/payment/info
        CONTENT_PAYMENT_INFO = API_BASE + "/api/v1/share/list/payment/info"

    class OfflinePath:
        # POST 域名 + /api/v1/offline/download
        DOWNLOAD = API_BASE + "/api/v1/offline/download"
        # GET 域名 + /api/v1/offline/download/process
        DOWNLOAD_PROCESS = API_BASE + "/api/v1/offline/download/process"


UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)  AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
ERROR_MAP = {}
