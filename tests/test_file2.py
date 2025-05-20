import shutil
from pathlib import Path

from cpan123 import Pan123openAPI

pan123 = Pan123openAPI()


#### 上传目录
def test_upload_dir():
    dirname = Path("tdata")
    pan123.upload_dir(dirname)
    print("上传完成")


#### 列出目录下的文件
def test_list_files():
    dirname = Path("/tdata")
    files = pan123.list_files(dirname)
    print(files)


#### 下载目录
def test_download_dir():
    dirname = Path("/tdata")
    pan123.download_dir(dirname, "tdata1")
    print("下载完成")


#### 删除目录
def test_delete_dir():
    dirname = Path("/tdata")
    pan123.delete_dir(dirname)
    print("删除完成")


#### 删除本地的目录
def test_delete_local_dir():
    dirname = Path("tdata1")
    if dirname.exists():
        shutil.rmtree(dirname)
        print("删除本地目录完成")
    else:
        print("目录不存在")


##### 默认找的是目录,返回, id,和 该 id 的详细信息
def test_find():
    fileId, fileId_item = pan123.find_file_id_by_path("/教科版高中物理")
    print("---" * 10)
    print("文件ID:", fileId)
    print("文件ID详细信息:", fileId_item)
    print("---" * 10)


def test_find2():
    # 找文件
    file = "/读秀相关工具/独秀机器人/Robot0309.zip"
    fileId, fileId_item = pan123.find_file_id_by_path(file, is_dir=False)
    print("---" * 10)
    print("文件ID:", fileId)
    print("文件ID详细信息:", fileId_item)
    print("---" * 10)


def test_find3():
    ## 实际是文件,但找的是目录,则会抛出异常
    file = "/读秀相关工具/独秀机器人/Robot0309.zip"
    error = False
    try:
        fileId, fileId_item = pan123.find_file_id_by_path(file, is_dir=True)
        print("---" * 10)
        print("文件ID:", fileId)
        print("文件ID详细信息:", fileId_item)
        print("---" * 10)
    except Exception as e:
        print(e)
        error = True
    assert error, "没有抛出异常"


if __name__ == "__main__":
    pass
    # test_delete_dir()
    test_upload_dir()
    # test_list_files()
    # test_download_dir()
    # test_find()
    # test_find2()
    # test_find3()
