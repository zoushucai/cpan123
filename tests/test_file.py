from pathlib import Path

from cpan123 import Pan123openAPI

pan123 = Pan123openAPI()


def test_pan123openapi():
    fname = "图吧工具箱2409安装程序.exe"
    pan123.download(fname, onlyurl=False)
    # 不知道为什么, 网盘上很多一模一样的文件,就是找不到(感觉是频率限制)

    fname = "图吧工具箱2409安装程序.exe"
    assert Path(fname).exists(), f"文件 {fname} 不存在"

    pan123.upload(fname, fname, 0, overwrite=True, duplicate=True)
    print("上传完成")


def test_list_v2():
    # 获取文件列表
    # file_list = pan123.file.list_v2(0, 10, "国科")
    # print(file_list.data)

    fileinfo = pan123.file.list_v2(0, 50)
    print("----" * 10)
    print(f"获取文件信息: \n{fileinfo.data}")


def test_detail():
    pan123 = Pan123openAPI()

    res = pan123.file.detail(fileID=12004772)
    print(res.data)


# if __name__ == "__main__":
#     test_pan123openapi()
#     # test_pan123openapi()
#     # test_detail()
