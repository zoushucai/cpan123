from pathlib import PurePosixPath

from cpanbd.file import File  # type: ignore
from cpanbd.utils.md5 import decrypt_md5  # type: ignore
from pydantic import validate_call

from .pan import Pan123openAPI


@validate_call
def baiduTo123(
    filebd: str,
    file123: str,
) -> bool:
    """
    百度网盘秒传到123网盘(前提是两边都有这个文件), 秒传成功返回 True, 否则返回 False

    百度网盘服务器上有这个文件, 123网盘服务器上也有这个文件, 才能秒传, 否则不上传到123网盘

    !!! note "注意"
        依赖 `cpanbd` 库, 请先安装 `pip install cpanbd`


    Args:
        filebd: 百度网盘文件路径 (绝对路径), 以 / 开头,只能是一个件
        file123: 115网盘文件路径 (绝对路径), 以 / 开头, 只能是一个文件

    Example:
        ```python
        from cpanbd import baiduTo123
        # 百度网盘文件路径
        filebd = "/BaiduNetdiskDownload/book/pdf/xxx.pdf"
        # 123网盘文件路径
        file123 = "/book/pdf/xxxx.pdf"
        baiduTo123(filebd, file123)
        ```

    """
    assert filebd.startswith("/"), "❌ 百度网盘文件路径必须以 / 开头"
    assert file123.startswith("/"), "❌ 123网盘文件路径必须以 / 开头"
    # 判断是文件而不是文件夹
    assert PurePosixPath(filebd).suffix != "", "❌ 百度网盘文件路径必须是文件"
    assert PurePosixPath(file123).suffix != "", "❌ 123网盘文件路径必须是文件"
    bddir = str(PurePosixPath(filebd).parent)
    bdname = str(PurePosixPath(filebd).name)

    # p123dir = str(PurePosixPath(file123).parent)
    # p123name = str(PurePosixPath(file123).name)
    file = File()
    pan123 = Pan123openAPI()
    listFiles = file.search(key=bdname, dir=bddir, web=0)
    if not listFiles or "list" not in listFiles:
        print("❌ 百度网盘搜索文件失败")
        return False

    fileinfo = None
    for item in listFiles["list"]:
        if item["path"] == filebd and item["isdir"] == 0:
            fileinfo = item
            break
    if not fileinfo:
        print("❌ 百度网盘文件不存在")
        return False
    filesize = fileinfo["size"]
    filemd5 = fileinfo["md5"]

    ### 上传到123网盘
    res = pan123.file.create(
        parentFileID=0,
        filename=file123,
        etag=decrypt_md5(filemd5),
        size=filesize,
        duplicate=1,  # 1 表示保留两者
        containDir=True,  # 是否包含目录
    )
    if res.data and res.data["reuse"] is True:
        print("✅ 成功秒传到123网盘")
        return True
    else:
        print("❌ 秒传失败")
        return False


if __name__ == "__main__":
    # 百度网盘文件路径
    filebd = "/BaiduNetdiskDownload/book/pdf/[伍德里奇]横截面与面板数据的经济计量分析(中文版).pdf"
    # 123网盘文件路径
    file123 = "/book/pdf/[伍德里奇]横截面与面板数据的经济计量分析(中文版).pdf"
    baiduTo123(filebd, file123)
