from cpan123 import Pan123openAPI

pan123 = Pan123openAPI()


def test_pan123openapi():
    #
    res = pan123.file.list(0, 100)
    print("----" * 10)
    print(f"获取文件列表: \n{res}")
    print("----" * 10)
    # 查找 图吧工具箱2409安装程序( 对应的fileID, 不要删除本体
    fileid = None
    assert res.data, "没有获取到文件列表"
    for item in res.data["fileList"]:
        if "图吧工具箱2409安装程序(" in item["filename"] and item["trashed"] == 0:
            fileid = item["fileId"]
            filename = item["filename"]
            break
    assert fileid, "没有找到文件ID"
    print("----" * 10)
    print(f"文件ID: {fileid}")
    print(f"文件名: {filename}")
    res = pan123.file.trash(fileIDs=[fileid])
    print("----" * 10)
    print(f"删除文件: \n{res}")
    print("----" * 10)
