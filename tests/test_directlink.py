from cpan123 import Pan123openAPI

pan123 = Pan123openAPI()


def test_directlink():
    # 启用直连空间, 传入的是文件夹id
    # fileinfo = pan123.file.list_v2(0, 50)
    # print("----" * 10)
    dirid = 22139321
    fileinfo = pan123.file.detail(fileID=dirid)
    print(f"获取文件信息: \n{fileinfo.data}")
    assert fileinfo.data, "获取文件信息失败"
    assert fileinfo.data["type"] == 1, "不是文件夹类型"
    # 获取文件夹里面的文件列表
    file_list = pan123.file.list_v2(dirid, 100)

    print("----" * 10)
    print(f"获取文件列表: \n{file_list.data}")

    res = pan123.directlink.enable(fileID=dirid)
    print("----" * 10)
    print(f"启用直连空间: \n{res.data}")

    # 获取直链链接( 这里是直连空间下的文件id)
    res = pan123.directlink.url(fileID=22139325)
    print("----" * 10)
    print(f"获取直链链接: \n{res.data}")

    # 禁用直连空间
    res = pan123.directlink.disable(fileID=dirid)
    print("----" * 10)
    print(f"禁用直连空间: \n{res.data}")
