import math
import os
import time
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import BinaryIO, Callable, List, Optional, Union

import requests
from py3_wget.main import download_file
from tenacity import retry, stop_after_attempt, wait_random

from .directlink import DirectLink
from .file import Auth, File
from .offline import Offline
from .oss import Oss
from .share import Share
from .user import User
from .utils.checkdata import UploadInChunks


class Pan123openAPI:
    """封装好的一些常用的 API 接口, 方便使用

    1. 文件上传
    2. 文件下载
    3. 图片上传到 OSS

    关于授权, 建议把授权信息放在环境变量中, 这样就不需要每次都输入了.

    1. 在终端中输入 `export PAN123TOKEN=xxxxxx` (Linux)
    2. windows 打开高级系统设置, 点击环境变量, 新建一个用户变量, 变量名为 `PAN123TOKEN`, 变量值为 `xxxxxx`
    3. 如果在环境变量中使用了 PAN123CLIENTID 和 PAN123CLIENTSECRET, 会自动更新token, 不需要手动更新

    环境变量:
        - PAN123TOKEN: 授权 token
        - PAN123TOKEN_EXPIREDAT: 授权 token 过期时间
        - PAN123CLIENTID: 客户端 ID
        - PAN123CLIENTSECRET: 客户端密钥

    Attributes:
        auth (Auth): 授权对象
        file (File): 文件对象
        share (Share): 分享对象
        offline (Offline): 离线下载对象
        user (User): 用户对象
        directlink (DirectLink): 直链对象
        oss (Oss): OSS 对象

    Example:
        ```python
        # 方式1: 使用环境变量中的授权信息
        from cpan123 import Pan123openAPI
        pan123 = Pan123openAPI() # 默认使用环境变量中的授权信息

        # 方式2: 使用授权信息
        from cpan123 import Pan123openAPI, Auth
        auth = Auth(clientID="your_client_id", clientSecret="your_client_secret")
        print(auth.access_token) # 打印 access_token

        # 或者
        auth = Auth(access_token="your_access_token")
        print(auth.access_token) # 打印 access_token

        # 然后传入 Pan123openAPI中
        pan123 = Pan123openAPI(auth=auth)
        ```
    """

    def __init__(
        self,
        auth: Optional[Auth] = None,
    ):
        self.auth = auth
        self.file = File(auth=self.auth)
        self.share = Share(auth=self.auth)
        self.offline = Offline(auth=self.auth)
        self.user = User(auth=self.auth)
        self.directlink = DirectLink(auth=self.auth)
        self.oss = Oss(auth=self.auth)

    def _validate_and_prepare_paths(
        self, filename: Union[str, Path], upload_name: Optional[Union[str, Path]] = None
    ) -> tuple[str, str]:
        """验证和准备文件路径

        Args:
            filename (Union[str, Path]): 本地文件路径
            upload_name (Optional[Union[str, Path]]): 上传到云端的文件名. 如果为 None,则使用本地文件名
        """

        filename = Path(filename) if not isinstance(filename, Path) else filename
        upload_name = Path(upload_name) if upload_name else filename.name

        if not filename.exists():
            raise ValueError(f"❌ 本地文件 {filename} 不存在")

        return str(filename), str(upload_name)

    def _find_existing_file(self, parentFileID: int, upload_name: str):
        """查找云端是否已存在同名文件

        Args:
            parentFileID (int): 父目录 ID
            upload_name (str): 上传的文件名
        """
        exist = self.file.list_v2(
            parentFileID,
            searchData=upload_name,
            limit=10,
            searchMode=1,
            skip=True,
        )
        matched_files = [
            f
            for f in (exist.fileList or [])
            if f["type"] == 0 and f["filename"] == upload_name and not f["trashed"]
        ]
        return matched_files

    def download(
        self, filename: str | list[str], onlyurl: bool = False, overwrite: bool = False
    ) -> List[dict] | None:
        """
        根据文件名下载文件(不覆盖). 只能获取根目录下的文件,不能获取子目录下的文件. 原因在于子目录难以筛选.

        采用的是 `pip install py3-wget` 作为下载工具,支持支持进度条、校验和验证、超时处理和下载失败时自动重试.

        已添加参数：

        - md5: 文件的 md5 值
        - max_tries: 最大重试次数 （默认 5 次）
        - retry_seconds: 重试间隔时间(秒) （默认 2 秒）



        参考： [https://123yunpan.yuque.com/org-wiki-123yunpan-muaork/cr6ced/fnf60phsushn8ip2](https://123yunpan.yuque.com/org-wiki-123yunpan-muaork/cr6ced/fnf60phsushn8ip2)

        Args:
            filename (str | list[str]): 单个文件名或文件名列表, 文件名会被存储到本地文件,如果本地有同名文件, 则会报错,可选强制覆盖
            onlyurl (bool, optional): 是否只获取下载链接. 默认直接下载文件.
            overwrite (bool): 是否覆盖同名文件. 默认 False.

        Returns:
            List[dict] | None: 返回下载链接列表或 None

        Raises:
            ValueError: 当输入文件名无效时


        Example:
            ```python
            from cpan123 import Pan123openAPI
            pan123 = Pan123openAPI()

            # # 下载单个文件
            fname = "xxxx.pt"
            pan123.download(fname)

            # # 下载多个文件
            # filenames = ["xxxx1.pt", "xxx2.pt"]
            # pan123.download(filenames)
            ```
        """
        # 参数标准化和验证
        if not filename:
            print("❌ 文件名不能为空")
            return None

        filenames = [filename] if isinstance(filename, str) else filename
        # 检查本地是否存在该文件
        need_down_files = []
        for fname in filenames:
            if Path(fname).exists():
                if not overwrite:
                    print(f"⚠️ 文件 {fname} 已存在,跳过下载")
                    continue
                Path(fname).unlink()
            need_down_files.append(fname)

        # 下载进度跟踪
        if not need_down_files:
            print("⚠️ 没有需要下载的文件")
            return None

        results = []
        for _idx, fname in enumerate(need_down_files):
            try:
                # 搜索文件
                response = self.file.list_v2(
                    parentFileId=0,
                    limit=100,
                    # searchData=str(fname),
                    # searchMode=1,  # 精准搜索
                )
                # 如果一个文件有多份,有些在回收站中, 有些在云端, 此时可能出现bug
                # 返回的结果全部都是回收站的, 优先返回非回收站的 (可能是缓存的缘故)
                # 保证搜索的文件,是文件, 精确匹配, 不在回收站中, 在根目录下
                matched_files = [
                    f
                    for f in (response.fileList or [])
                    if f["type"] == 0
                    and f["filename"] == fname
                    and f["trashed"] == 0
                    and f["parentFileId"] == 0
                ]

                if not matched_files:
                    print(f"⚠️ 文件 {fname} 在云端的根目录下找不到!!!")
                    warnings.warn(f"未找到文件 {fname}", stacklevel=2)
                    continue

                target_file = matched_files[0]
                # if target_file["trashed"] == 1:
                #     print(f"⚠️ 文件 {fname} 在云端的回收站中,尝试下载")

                download_res = self.file.download_info(target_file["fileId"])
                download_url = download_res.downloadUrl
                if not download_url:
                    warnings.warn(f"无法获取 {fname} 的下载链接", stacklevel=2)
                    continue
                down_info = {
                    "url": download_url,
                    "filename": target_file["filename"],
                    "md5": target_file["etag"],
                }
                if onlyurl:
                    results.append(down_info)
                    continue
                else:
                    download_file(
                        url=down_info["url"],
                        output_path=down_info["filename"],
                        md5=down_info["md5"],
                        max_tries=5,  # Maximum number of retry attempts
                        retry_seconds=2,  # Initial retry delay in seconds
                    )
            except Exception as e:
                warnings.warn(f"下载 {fname} 时出错: {str(e)}", stacklevel=2)
                continue
        return results if onlyurl else None

    @retry(stop=stop_after_attempt(50), wait=wait_random(min=1, max=5))
    def _upload_file_data_common(
        self,
        get_upload_url_func: Callable,
        f: BinaryIO,
        preuploadID: int,
        start_seek: int,
        length: int,
        idx: int,
        task_upload_per: list,
    ) -> bool:
        """通用分片上传"""
        data_response = get_upload_url_func(preuploadID, idx + 1)
        presignedURL = data_response.data["presignedURL"]
        assert presignedURL, "获取 presignedURL 失败"
        f.seek(start_seek)
        requests.put(
            presignedURL,
            data=UploadInChunks(f, length, idx, task_upload_per, chunksize=1024),
            timeout=60,
        )
        task_upload_per[idx] = 100
        return True

    def _upload_common(
        self,
        filename: Union[str, Path],
        upload_name: Optional[Union[str, Path]],
        parentFileID: Union[int, str],
        overwrite: bool,
        use_oss: bool = False,
    ) -> int:
        """通用上传逻辑

        Args:
            filename (str | Path): 上传的文件名
            upload_name (str | Path, optional): 上传云端的文件名. 如果为 None,则使用本地文件名.
            parentFileID (int, optional): 上传到云端的目录 ID. 默认为根目录下, 如果使用use_oss,则为云端根目录为空, 如果不使用oss,则为云端目录为0
            overwrite (bool, optional): 是否强制覆盖同名文件. 如果云端存在同名文件,则默认会报错.
            use_oss (bool, optional): 是否使用 OSS 上传. 默认为 False.

        Returns:
            int: 文件 ID 或 -1

        """
        filename, upload_name = self._validate_and_prepare_paths(filename, upload_name)

        file_etag = self.file.calculate_md5(filename)
        file_size = Path(filename).stat().st_size
        uploader = self.oss if use_oss else self.file

        # OSS 不能列文件
        if not use_oss:
            if not isinstance(parentFileID, int):
                raise ValueError("parentFileID 必须为 int 类型")
            matched_files = self._find_existing_file(parentFileID, upload_name)
            if matched_files and not overwrite:
                warnings.warn(
                    f"云端文件 {upload_name} 已存在,请更换文件名", stacklevel=2
                )
                return -1
            if matched_files and overwrite:
                fileId = matched_files[0]["fileId"]
                if isinstance(fileId, int):
                    fileId = [fileId]
                if not isinstance(fileId, list):
                    print("❌ fileId 不是list类型,强制删除失败, 退出")
                    return -1

                self.file.trash(fileId)
                warnings.warn(
                    f"云端文件 {upload_name} 已强制移除到回收站", stacklevel=2
                )

        with open(filename, "rb") as f:
            f.seek(0)
            create_kwargs = {
                "parentFileID": parentFileID,
                "filename": upload_name,
                "etag": file_etag,
                "size": file_size,
            }
            if use_oss:
                create_kwargs["type"] = 1

            data_response = uploader.create(**create_kwargs)
            if data_response.code != 0:
                raise ValueError(data_response.message)

            if data_response.data is None:
                raise ValueError("上传接口返回数据为空，无法获取preuploadID等信息")

            if data_response.data is not None and data_response.data.get("reuse"):
                print("✅ 秒传成功....")
                return data_response.data["fileID"]

            preuploadID = data_response.data["preuploadID"]
            sliceSize = data_response.data["sliceSize"]
            total_sliceNo = math.ceil(file_size / sliceSize)
            task_upload_per = [0.0] * total_sliceNo

            def upload_slice(sliceNo):
                start = sliceNo * sliceSize
                size = min(sliceSize, file_size - start)
                with open(filename, "rb") as f_slice:
                    f_slice.seek(start)
                    return self._upload_file_data_common(
                        uploader.get_upload_url,
                        f_slice,
                        preuploadID,
                        start,
                        size,
                        sliceNo,
                        task_upload_per,
                    )

            cpu_count = os.cpu_count() or 1
            max_workers = min(max(1, cpu_count - 1), total_sliceNo)
            print("ℹ️ 开始上传到云端...")
            print(f"ℹ️ 文件被拆成 {total_sliceNo} 个分片, 分片大小: {sliceSize} 字节")
            print(f"ℹ️ 用 {max_workers} 个线程一起上传哦~")

            if max_workers == 1:
                for i in range(total_sliceNo):
                    if not upload_slice(i):
                        print(f"\nℹ️分片 {i} 上传失败,终止上传.")
                        return -1
                    avg = sum(task_upload_per) / total_sliceNo
                    print(f"\rℹ️进度: {avg:.1f}%(共{total_sliceNo}分片)", end="")
            else:
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    future_to_slice = {
                        executor.submit(upload_slice, i): i
                        for i in range(total_sliceNo)
                    }
                    for future in as_completed(future_to_slice):
                        slice_id = future_to_slice[future]
                        if not future.result():
                            print(f"\nℹ️分片 {slice_id} 上传失败,终止上传.")
                            return -1
                        avg = sum(task_upload_per) / total_sliceNo
                        print(f"\rℹ️进度: {avg:.1f}%(共{total_sliceNo}分片)", end="")

            print("\nℹ️分片上传完成,开始合并分片...")
            complete_response = uploader.upload_complete(preuploadID)
            if complete_response.data is not None and complete_response.data.get(
                "completed"
            ):
                print("✅ 文件上传完成")
                return complete_response.data["fileID"]

            if complete_response.data is not None and complete_response.data.get(
                "async"
            ):
                while True:
                    time.sleep(2)
                    data_response = uploader.upload_async_result(preuploadID)
                    if data_response.data is not None and data_response.data.get(
                        "completed"
                    ):
                        print("✅ 文件上传完成")
                        return data_response.data["fileID"]
        return -1

    def upload(
        self,
        filename: Union[str, Path],
        upload_name: Optional[Union[str, Path]] = None,
        parentFileID: Union[int, str] = 0,
        overwrite: bool = False,
    ) -> int:
        """上传文件. 失败返回 -1,成功返回文件 ID. (只能处理文件,不能处理目录,且文件默认为根目录下, 主要是更目录的id为0, 比较方便)

        Args:
            filename (str | Path): 上传的文件名
            upload_name (str | Path, optional): 上传云端的文件名. 如果为 None,则使用本地文件名.
            parentFileID (int, optional): 上传到云端的目录 ID. 默认为根目录下
            overwrite (bool, optional): 是否强制覆盖同名文件. 如果云端存在同名文件,则默认会报错.

        Returns:
            int: 文件 ID 或 -1

        Example:
            ```python
            from cpan123 import Pan123openAPI
            pan123 = Pan123openAPI()
            # 上传文件
            fname = "xxxxx.zip"
            pan123.upload(fname, fname, 0, overwrite=True)
            print("上传完成")
            ```

        """
        res = self._upload_common(filename, upload_name, parentFileID, overwrite, False)
        return res

    def upload_oss(
        self,
        filename: Union[str, Path],
        upload_name: Optional[Union[str, Path]] = None,
        parentFileID: Union[int, str] = "",
        overwrite: bool = False,
    ) -> int:
        """上传文件到oss(图床). 失败返回 -1,成功返回文件 ID.(建议根目录)

        Args:
            filename (str | Path): 上传的文件名
            upload_name (str | Path, optional): 上传云端的文件名. 如果为 None,则使用本地文件名.
            parentFileID (int, optional): 上传到云端的目录 ID. 默认为根目录下
            overwrite (bool, optional): 是否强制覆盖同名文件. 如果云端存在同名文件,则默认会报错.

        Returns:
            int: 文件 ID 或 -1

        Example:
            ```python
            from cpan123 import Pan123openAPI
            pan123 = Pan123openAPI()
            # 上传文件到oss(图床)
            imgfile = "xxxx.png"
            res = pan123.upload_oss(imgfile, Path(imgfile).name)
            print(res)
            ```
        """
        res = self._upload_common(filename, upload_name, parentFileID, overwrite, True)
        return res


if __name__ == "__main__":
    pan123 = Pan123openAPI()
    # # 下载单个文件
    fname = "word3prefect6300data.rar"
    pan123.download(fname, onlyurl=False)

    # # # 上传文件
    # pan123.upload(fname, fname, 0, overwrite=True)
    # print("上传完成")
