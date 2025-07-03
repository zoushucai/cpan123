import math
import os
import time
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path, PurePosixPath
from typing import Any, BinaryIO, Callable, List, Optional, Sequence, Union

import requests
from py3_wget.main import download_file
from pydantic import BaseModel, TypeAdapter, validate_call
from tenacity import retry, stop_after_attempt, wait_random
from tqdm import tqdm

from .directlink import DirectLink
from .file import Auth, File
from .offline import Offline
from .oss import Oss
from .share import Share
from .user import User
from .utils.checkdata import UploadInChunks

# # 定义允许的单个类型
# SingleDirType = Union[str, int, Path, PurePosixPath]

# # 定义参数类型,可以是单个值或这些值的序列对象
# DirnamesType = Union[SingleDirType, Iterable[SingleDirType]]


class FileItem(BaseModel):
    fileId: int
    filename: str
    full_path: str
    relative_path: str
    etag: str
    model_config = {"extra": "allow"}


class Pan123openAPI:
    """封装好的一些常用的 API 接口, 方便使用

    1. 文件上传
    2. 文件下载
    3. 图片上传到 OSS

    授权信息参考: [Auth](./auth.md)

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
        from cpan123 import Pan123openAPI
        pan123 = Pan123openAPI()

        # 下载单个文件
        fname = "xxxx.pt"
        pan123.download(fname)

        # 上传文件
        fname = "xxxxx.zip"
        pan123.upload(fname, fname, 0, overwrite=True)

        # 上传目录
        dirname = Path("tdata")
        pan123.upload_dir(dirname)

        # 列出目录下的所有文件(递归且包含目录本身)
        dirname = Path("/tdata")
        files = pan123.list_files(dirname)

        # 下载目录(从网盘/data 目录 下载到本地 tdata1 目录)
        dirname = Path("/tdata")
        pan123.download_dir(dirname, "tdata1")

        # 删除目录
        dirname = Path("/tdata")
        pan123.delete_dir(dirname)

        # 根据路径查找文件 ID以及文件信息
        file = "/xxx/xxx.zip"
        fileId, fileId_item = pan123.find_file_id_by_path(file, is_dir=False)
        ```
    """

    def __init__(
        self,
        auth: Optional[Auth] = None,
    ):
        self.auth = auth if auth is not None else Auth()
        if not isinstance(self.auth, Auth):
            raise ValueError("auth 必须是 Auth 对象")
        self.file = File(auth=self.auth)
        self.share = Share(auth=self.auth)
        self.offline = Offline(auth=self.auth)
        self.user = User(auth=self.auth)
        self.directlink = DirectLink(auth=self.auth)
        self.oss = Oss(auth=self.auth)
        self._remote_path_cache = {}

    def _validate_and_prepare_paths(
        self,
        filename: Union[str, Path, PurePosixPath],
        upload_name: Union[str, Path, PurePosixPath, None] = None,
    ) -> tuple[str, str]:
        """验证和准备文件路径(本地路径和上传路径)

        1. 如果本地文件不存在,则抛出异常
        2. 如果 upload_name 为 None,则使用本地文件名, 否则使用 upload_name定义的文件名

        Args:
            filename (Union[str, Path, PurePosixPath]): 本地文件路径
            upload_name (Union[str, Path, PurePosixPath, None]): 上传到云端的文件名. 如果为 None,则使用本地文件名
        """

        filename = Path(filename) if not isinstance(filename, Path) else filename
        upload_name = Path(upload_name) if upload_name else Path(filename).name

        if not filename.exists():
            raise ValueError(f"❌ 本地文件 {filename} 不存在")

        return str(filename), str(upload_name)

    @validate_call
    def download(
        self,
        filename: Union[str, Path, List[Union[str, Path]]],
        onlyurl: bool = False,
        overwrite: bool = False,
    ) -> List[dict] | None:
        """根据文件名下载文件(不覆盖).

        采用的是 `pip install py3-wget` 作为下载工具,支持支持进度条、校验和验证、超时处理和下载失败时自动重试.

        已添加参数:

        - md5: 文件的 md5 值
        - max_tries: 最大重试次数 (默认 5 次)
        - retry_seconds: 重试间隔时间(秒) (默认 2 秒)


        Args:
            filename (Union[str, Path, List[Union[str, Path]]]): 单个文件名或文件名列表, 文件名会被存储到本地文件,如果本地有同名文件, 则会报错,可选强制覆盖, 如果使用相对路径, 则默认在根目录下
            onlyurl (bool): 是否只获取下载链接. 默认直接下载文件.
            overwrite (bool): 是否覆盖同名文件. 默认 False.

        Returns:
            若 onlyurl 为 True, 返回下载链接列表; 否则返回 None.

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
        filename = [filename] if isinstance(filename, (str, Path)) else filename
        if not isinstance(filename, list):
            raise ValueError("filename 必须是字符串或 Path 的列表")

        if not all(isinstance(fname, (str, Path)) for fname in filename):
            raise ValueError("filename 必须是字符串或 Path 的列表")

        # 检查本地是否存在该文件
        need_down_files = []
        for fname in filename:
            if Path(fname).exists():
                if not overwrite:
                    print(f"⚠️ 文件 {fname} 已存在,跳过下载")
                    continue
                print(f"⚠️ 文件 {fname} 已存在,将删除...")
                Path(fname).unlink()
            need_down_files.append(fname)

        # 下载进度跟踪
        if not need_down_files:
            print("⚠️ 没有需要下载的文件")
            return None

        results = []
        need_down_files = [Path(fname) for fname in need_down_files]
        for _idx, fname in enumerate(need_down_files):
            try:
                # # 构造云端路径
                if not fname.is_absolute():
                    fname = PurePosixPath("/") / str(fname).lstrip("./")

                if not fname.suffix:
                    # 假设没有后缀名的文件是目录
                    print(f"❌ 文件 {fname} 没有后缀名,跳过下载")
                    continue

                fileId, fileItem = self.find_file_id_by_path(
                    fname, root_id=0, is_dir=False
                )
                if not fileId or not fileItem:
                    print(f"❌ 文件 {fname} 找不到")
                    continue

                download_res = self.file.download_info(fileId)
                download_url = download_res.downloadUrl
                if not download_url:
                    warnings.warn(f"无法获取 {fname} 的下载链接", stacklevel=2)
                    continue
                down_info = {
                    "url": download_url,
                    "filename": fileItem["filename"],
                    "md5": fileItem["etag"],
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

    @retry(stop=stop_after_attempt(10), wait=wait_random(min=1, max=5))
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

    @validate_call
    def _upload_common(
        self,
        filename: Union[str, Path],
        upload_name: Union[str, Path, None, PurePosixPath],
        parentFileID: Union[int, str],
        overwrite: bool,
        use_oss: bool = False,
        duplicate: None | int = None,
        containDir: bool = False,
    ) -> int:
        """通用上传逻辑

        Args:
            filename (str | Path): 上传的文件名
            upload_name (str | Path | None): 上传云端的文件名. 如果为 None,则使用本地文件名. 可以使用多级目录,如 "a/b/c.txt",如果是相对路径,则会相对于根目录上传,如果是绝对路径,则会直接使用该路径.(前提是云端相关的目录已经存在)
            parentFileID (int | str): 上传到云端的目录 ID. 默认为根目录下, 如果使用use_oss,则为云端根目录为空, 如果不使用oss,则为云端目录为0, 如果上传到子目录中,则会自动查找父目录的 ID并纠正,如果不存在,则会报错.
            overwrite (bool): 是否强制覆盖同名文件. 如果云端存在同名文件,则默认会报错.
            use_oss (bool ): 是否使用 OSS 上传. 默认为 False.
            duplicate (int | None): 当有相同文件名时,文件处理策略(1保留两者,新文件名将自动添加后缀,2覆盖原文件) 如果 overwrite 为 True, 则默认为 2
            containDir (bool): 上传文件是否包含路径,默认 False,

        Returns:
            文件 ID 或 -1

        """
        filename, upload_name = self._validate_and_prepare_paths(filename, upload_name)

        file_etag = self.file.calculate_md5(filename)
        file_size = Path(filename).stat().st_size
        uploader = self.oss if use_oss else self.file

        if overwrite:
            if duplicate is None:
                duplicate = 2  # 默认覆盖原文件
        # OSS 不能列文件
        if not use_oss:
            if not isinstance(parentFileID, int):
                raise ValueError("parentFileID 必须为 int 类型")
            if not Path(upload_name).is_absolute():
                need_find_name = str(PurePosixPath("/") / str(upload_name).lstrip("./"))
            else:
                need_find_name = str(upload_name).strip()
            # 如果有目录,查找目录的 id
            if str(Path(need_find_name).parent) not in ["", "/"]:
                # 如果父目录不是根目录,则为上传到根目录下的子目录下
                file_id, _ = self.find_file_id_by_path(
                    str(Path(need_find_name).parent), root_id=0, is_dir=True
                )
                if not file_id:
                    raise ValueError(
                        f"找不到目录 {Path(need_find_name).parent},请先创建"
                    )
                else:
                    parentFileID = int(file_id)

            if parentFileID == 0:
                file_id, file_item = self.find_file_id_by_path(
                    str(need_find_name), root_id=parentFileID, is_dir=False
                )
                if file_id and overwrite:
                    if isinstance(file_id, int):
                        file_id = [file_id]
                    if not isinstance(file_id, list):
                        print("❌ fileId 不是list类型,强制删除失败, 退出")
                        return -1
                    trash_out = self.file.trash(fileIDs=file_id, skip=True)
                    # self.file.delete(fileIDs=file_id, skip=True)
                    print(
                        f"✅ 云端文件 {need_find_name} 移动到回收站, message: {trash_out.message}"
                    )

        with open(filename, "rb") as f:
            f.seek(0)
            create_kwargs = {
                "parentFileID": parentFileID,
                "filename": str(Path(upload_name).name),
                "etag": file_etag,
                "size": file_size,
                "duplicate": duplicate,
                "containDir": containDir,
            }
            if use_oss:
                create_kwargs["type"] = 1
                create_kwargs.pop("duplicate", None)
                create_kwargs.pop("containDir", None)

            data_response = uploader.create(**create_kwargs)
            if data_response.code != 0:
                raise ValueError(data_response.message)

            if data_response.data is None:
                raise ValueError("上传接口返回数据为空,无法获取preuploadID等信息")

            if data_response.data is not None and data_response.data.get("reuse"):
                print("✅ 秒传成功....")
                return data_response.data["fileID"]

            preuploadID = data_response.data["preuploadID"]
            # print("preuploadID:", preuploadID)
            sliceSize = data_response.data["sliceSize"]
            total_sliceNo = math.ceil(file_size / sliceSize)
            task_upload_per = [0.0] * total_sliceNo

            def upload_slice(sliceNo):
                start = sliceNo * sliceSize
                size = min(sliceSize, file_size - start)
                with open(filename, "rb") as f_slice:
                    f_slice.seek(start)
                    t0 = time.time()
                    success = self._upload_file_data_common(
                        uploader.get_upload_url,
                        f_slice,
                        preuploadID,
                        start,
                        size,
                        sliceNo,
                        task_upload_per,
                    )
                    t1 = time.time()
                duration = t1 - t0
                return success, sliceNo, size, duration

            cpu_count = os.cpu_count() or 1
            max_workers = min(max(1, cpu_count - 1), total_sliceNo)
            m1 = sliceSize // 1024 // 1024
            w1 = max_workers
            t1 = total_sliceNo
            t2 = file_size // 1024 // 1024
            print(f"✅ {w1} 线程上传 {t1} 分片, 单分片<= {m1} MB,共 {t2:.2f} MB")
            uploaded_bytes = 0
            total_time = 0
            if w1 <= 1:
                # 不应该使用多线程,直接上传
                for i in range(total_sliceNo):
                    success, slice_id, size, duration = upload_slice(i)
                    if not success:
                        print(f"❌ 分片 {slice_id} 上传失败，终止上传。")
                        return -1
                    uploaded_bytes += size
                    total_time += duration
                    speed = uploaded_bytes / total_time if total_time > 0 else 0
            else:
                with tqdm(total=t1, desc="上传进度", unit="slice") as pbar:
                    with ThreadPoolExecutor(max_workers=max_workers) as executor:
                        futures = {
                            executor.submit(upload_slice, i): i
                            for i in range(total_sliceNo)
                        }
                        for future in as_completed(futures):
                            success, slice_id, size, duration = future.result()
                            if not success:
                                print(f"❌ 分片 {slice_id} 上传失败，终止上传。")
                                return -1
                            uploaded_bytes += size
                            total_time += duration
                            speed = uploaded_bytes / total_time if total_time > 0 else 0
                            speed_str = (
                                f"{speed / 1024 / 1024:.2f} MB/s"
                                if speed > 1024 * 1024
                                else f"{speed / 1024:.2f} KB/s"
                            )
                            pbar.set_postfix_str(f"速度: {speed_str}")
                            pbar.update(1)
                print("✅ 分片上传完成, 开始合并分片...")
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

    @validate_call
    def upload(
        self,
        filename: Union[str, Path],
        upload_name: Union[str, Path, None] = None,
        parentFileID: Union[int, str] = 0,
        overwrite: bool = False,
        duplicate: None | int = None,
        containDir: bool = False,
    ) -> int:
        """上传文件. 失败返回 -1,成功返回文件 ID. (只能处理文件,不能处理目录)

        Args:
            filename (str | Path): 上传的文件名
            upload_name (str | Path | None): 上传云端的文件名. 如果为 None,则使用本地文件名.
            parentFileID (int, str): 上传到云端的目录 ID. 默认为根目录下
            overwrite (bool): 是否强制覆盖同名文件. 如果云端存在同名文件,则默认会报错. 这个是先移除到回收站,再上传
            duplicate (int): 当有相同文件名时,文件处理策略(1保留两者,新文件名将自动添加后缀,2覆盖原文件)
            containDir (bool): 上传文件是否包含路径,默认 False.

        Returns:
            文件 ID 或 -1

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
        # 排除 .开头的文件
        # if Path(filename).name.startswith("."):
        #     print(f"❌ 文件 {filename} 不能以 '.' 开头")
        #     return -1
        res = self._upload_common(
            filename, upload_name, parentFileID, overwrite, False, duplicate, containDir
        )
        return res

    @validate_call
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
            文件 ID 或 -1

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

    @validate_call
    def find_file_id_by_path(
        self, path: str | PurePosixPath | Path, root_id: int = 0, is_dir: bool = True
    ) -> tuple[int, dict] | tuple[None, None]:
        """根据绝对路径查找对应文件(夹)的 fileId.

        该方法会递归查找路径中的每个部分,直到找到目标文件(夹)为止.

        - 如果路径中有部分不存在,则返回 None.
        - 注意:该方法仅支持绝对路径,且路径必须以 '/' 开头.
        - 例如:'/A/B/C' 是合法的绝对路径,而 'A/B/C' 不是.

        Args:
            path (str | PurePosixPath | Path): 云盘中的绝对路径,如 /A/B/C.
            root_id (int): 起始根目录 fileId, 默认从 0 开始.
            is_dir (bool): True 表示查找目录, False 表示查找文件.

        Returns:
            如果找到,返回包含 fileId 和文件信息字典的元组；如果未找到,返回 `(None, None)`.
        """
        path = PurePosixPath(path)
        if not path.is_absolute():
            raise ValueError("路径必须是绝对路径")
        if path.suffix and is_dir:
            raise ValueError("请求提供目录路径而不是文件路径")
        if not path.suffix and not is_dir:
            raise ValueError("请求提供文件路径而不是目录路径")

        parts = path.parts[1:]  # 忽略根 "/"
        current_id = root_id
        current_item = None
        for index, name in enumerate(parts):
            found = False
            last_file_id = None
            while True:
                res = self.file.list_v2(
                    parentFileId=current_id, lastFileId=last_file_id, limit=100
                )
                if not res.data or not res.data.get("fileList"):
                    print(f"❌ 在 {current_id} 下没有找到任何文件")
                    break

                for item in res.data["fileList"]:
                    if item["filename"] == name and item["trashed"] == 0:
                        # 中间部分必须是目录
                        if index < len(parts) - 1 and item["type"] != 1:
                            continue

                        # 最后一部分根据 is_dir 判断类型
                        if index == len(parts) - 1 and (
                            (is_dir and item["type"] != 1)
                            or (not is_dir and item["type"] != 0)
                        ):
                            continue
                        current_id = item["fileId"]
                        current_item = item
                        found = True
                        break

                if found:
                    break

                last_file_id = res.data.get("lastFileId", -1)
                if last_file_id == -1:
                    break

            if not found:
                return None, None
        if current_item is None:
            return None, None
        else:
            return current_item["fileId"], current_item

    @validate_call
    def _get_file_list(
        self, parentFileId: int, current_path: str = "", base_path: str = ""
    ) -> list[dict[str, Any]]:
        """
        递归获取指定 parentFileId 下的所有文件(包含子文件夹本身)

        Args:
            parentFileId (int): 当前目录的 fileId.
            current_path (str): 当前正在递归的完整路径(用于构造 full_path).
            base_path (str): 用户原始请求的基准路径(用于计算 relative_path).

        Returns:
            包含所有文件信息的字典列表,每项包含 full_path 和 relative_path 字段.
        """
        file_list = []
        lastFileId = None

        while True:
            res = self.file.list_v2(
                parentFileId=parentFileId, lastFileId=lastFileId, limit=100
            )

            if not res.data or not res.data.get("fileList"):
                break

            for item in res.data["fileList"]:
                item_path = f"{current_path}/{item['filename']}".rstrip("/")
                item["full_path"] = item_path

                # 计算相对路径(相对于 base_path)
                if base_path:
                    try:
                        relative_path = str(
                            PurePosixPath(item_path).relative_to(base_path)
                        )
                    except ValueError:
                        relative_path = item["filename"]
                else:
                    relative_path = item["filename"]

                item["relative_path"] = relative_path or "."

                # 如果是目录,则递归
                if item["type"] == 1:
                    file_list.append(item)  # 目录本身
                    file_list.extend(
                        self._get_file_list(item["fileId"], item_path, base_path)
                    )
                else:
                    file_list.append(item)

            lastFileId = res.data.get("lastFileId", -1)
            if lastFileId == -1:
                break

        # 检查每一项都是 dict,且含有 fileId 和 filename 字段,以及 full_path 和 relative_path 字段
        TypeAdapter(list[FileItem]).validate_python(file_list)
        return file_list

    @validate_call
    def list_files(
        self, dirnames: Sequence[Union[str, int, Path, PurePosixPath]]
    ) -> list[dict] | None:
        """
        给定一个绝对目录路径,列出其下所有文件(含子目录)以及查询目录本身的文件信息.

        Args:
            dirnames (Sequence[Union[str, int, Path, PurePosixPath]]): 云盘中的绝对路径目录列表,必须以 '/' 开头或为整数 fileId.

        Returns:
            所有目录下的文件信息列表(包含 full_path 和 relative_path 字段).  如果没有找到目录,则返回 None.
        """
        all_files = []
        if not dirnames:
            print("❌ 目录名不能为空")
            return None

        if isinstance(dirnames, (str, int, Path, PurePosixPath)):
            dirnames = [dirnames]
        if isinstance(dirnames, list) and not all(
            isinstance(dirname, (str, int, Path, PurePosixPath)) for dirname in dirnames
        ):
            raise ValueError("dirnames 必须是字符串或 PurePosixPath 的列表")

        for dirname in dirnames:
            if isinstance(dirname, (str, PurePosixPath, Path)):
                dirname = PurePosixPath(dirname)
                # 校验
                if not dirname.is_absolute():
                    print(f"❌ 跳过非法路径: {dirname}(必须是绝对路径)")
                    continue
                if dirname.suffix:
                    print(f"❌ 跳过文件路径: {dirname}(必须是目录)")
                    continue
                if dirname == PurePosixPath("/"):
                    print("⚠️ 跳过根目录, 请指定更具体的文件夹)")
                    continue
                # 获取 fileId 并递归查找文件
                file_id, file_item = self.find_file_id_by_path(dirname)
                if file_id is None:
                    print("❌ 没有找到该目录")
                    return None
            elif isinstance(dirname, int):
                # 如果是整数,直接使用
                file_id = dirname

            files = self._get_file_list(
                file_id, current_path=str(dirname), base_path=str(dirname)
            )
            if files is None:
                continue
            # 获取目录本身的 id
            thisdir = self.file.infos([file_id])
            if (
                thisdir.data
                and thisdir.data.get("fileList")
                and len(thisdir.data["fileList"]) == 1
            ):
                data = thisdir.data["fileList"][0]
                data["full_path"] = str(dirname)
                data["relative_path"] = "."
                all_files.append(data)
            all_files.extend(files)

        # 检查每一项都是 dict,且含有 fileId 和 filename 字段,以及 full_path 和 relative_path 字段
        TypeAdapter(list[FileItem]).validate_python(all_files)
        return all_files

    @validate_call
    def _download_single_file(self, file: dict, output_path: str | Path = ".") -> None:
        """
        下载单个文件到指定路径.

        Args:
            file (dict): 文件信息字典,必须包含 'fileId' 和 'etag' 字段.
            output_path (str | Path): 下载保存的目录,默认当前目录.

        Returns:
            None
        """
        # 过滤掉回收站的文件
        if file["trashed"] == 1:
            return
        # 过滤掉目录
        if file["type"] == 1:
            # temp_path = Path(output_path) / file["relative_path"]
            # Path(temp_path).mkdir(parents=True, exist_ok=True)
            return
        download_url = self.file.download_info(file["fileId"]).downloadUrl
        if not download_url:
            print(f"❌ 无法获取下载链接: {file['relative_path']}")
            return
        local_path = Path(output_path) / file["relative_path"]
        Path(local_path).parent.mkdir(parents=True, exist_ok=True)
        download_file(
            url=download_url,
            output_path=str(local_path),
            md5=file["etag"],
            overwrite=True,
            max_tries=5,
            retry_seconds=2,
        )

    @validate_call
    def download_dir(
        self,
        dirnames: Sequence[Union[str, int, Path, PurePosixPath]]
        | Union[str, int, Path, PurePosixPath],
        output_path: Optional[Union[str, Path]] = None,
    ) -> None:
        """
        下载指定目录下的所有文件(含子目录).

        Args:
            dirnames: 云盘中的绝对路径目录列表或单个路径，必须以 '/' 开头或为整数 fileId。
            output_path: 下载保存的目录。如果未指定，则使用云端目录名作为输出目录。

        Returns:
            None
        """
        # 转换为列表
        if isinstance(dirnames, (str, int, Path, PurePosixPath)):
            dirnames = [dirnames]

        # 循环处理每一个云端目录
        for dirname in dirnames:
            # 获取文件列表（包含子文件）
            all_files = self.list_files([dirname])
            if not all_files:
                print(f"❌ 没有找到该目录: {dirname}")
                continue

            # 自动决定输出目录
            if output_path is None or str(output_path) == ".":
                if isinstance(dirname, int):
                    local_out = Path(str(dirname))
                else:
                    local_out = Path(str(dirname)).name  # 取最后一级路径名
            else:
                local_out = Path(output_path)

            local_out = Path(local_out)
            local_out.mkdir(parents=True, exist_ok=True)

            for file in all_files:
                # 下载所有子文件（不要误跳过）
                self._download_single_file(file, local_out)

    @validate_call
    def _ensure_remote_path(self, path: Path, root_id: int) -> int:
        """
        确保 path 路径在云端存在，并返回对应目录 ID。
        - path: 相对于某个根的路径，如 Path("a/b/c")
        - root_id: 起始目录 ID(通常是 0)
        """
        if not path or str(path) in (".", ""):
            return root_id

        if path in self._remote_path_cache:
            return self._remote_path_cache[path]

        current_id = root_id
        current_path = Path()

        for part in path.parts:
            current_path = current_path / part

            if current_path in self._remote_path_cache:
                current_id = self._remote_path_cache[current_path]
                continue

            # 调用 API 创建目录
            res = self.file.mkdir(part, current_id)
            if not res or res.data is None or res.code != 0:
                raise RuntimeError(
                    f"❌ 创建目录失败: {part} (父ID: {current_id}) - 返回: {res.message}"
                )

            current_id = res.data["dirID"]
            self._remote_path_cache[current_path] = current_id

        return current_id

    @validate_call
    def upload_dir(self, local_dir: Path | str, root_id: int = 0):
        """
        上传本地目录（递归子目录）到云端指定父目录 ID

        Args:
            local_dir (Path | str): 本地目录路径,必须是绝对路径.
            root_id (int): 云端目标父目录的 ID, 默认为根目录为 0.
        """
        self._remote_path_cache = {}  # 清空缓存
        local_dir = Path(local_dir) if isinstance(local_dir, str) else local_dir
        local_dir = local_dir.resolve()  # 确保是绝对路径

        # 先创建顶层目录
        top_path = Path(local_dir.name)
        top_level_id = self._ensure_remote_path(top_path, root_id)

        # 将 "." 映射为顶级目录
        self._remote_path_cache[Path(".")] = top_level_id

        for file_path in local_dir.rglob("*"):
            if file_path.is_file():
                relative_path = file_path.relative_to(local_dir)
                parent_dir = relative_path.parent  # 可能是 "."

                # 创建父目录路径（在顶层目录下递归创建）
                remote_parent_id = self._ensure_remote_path(parent_dir, top_level_id)
                # 上传
                self.upload(file_path, file_path.name, remote_parent_id)
        # 清空缓存
        self._remote_path_cache = {}

    @validate_call
    def delete_dir(
        self, dirnames: Sequence[Union[str, int, Path, PurePosixPath]]
    ) -> None:
        """
        删除指定目录及其下的所有文件(含子目录).

        Args:
            dirnames (Sequence[Union[str, int, Path, PurePosixPath]]): 云盘中的绝对路径目录列表,必须以 '/' 开头或为整数 fileId.

        Returns:
            None
        """
        all_files = self.list_files(dirnames)
        if all_files is None:
            print("❌ 没有找到该目录")
            return
        if len(all_files) == 0:
            print("❌ 目录下没有文件")
            return
        all_files_id = [file["fileId"] for file in all_files if file["trashed"] == 0]
        if not all_files_id:
            print("❌ 目录下没有文件")
            return
        ######  好像不能批量删除,只能单个删除
        ## 单个的删除
        [self.file.trash([file_id]) for file_id in all_files_id]
        print("✅ 删除完成")

        ##### 批量删除
        # n = len(all_files_id)
        # for i in range(0, n, 100):
        #     if i + 100 > n:
        #         batch_ids = all_files_id[i:]
        #     else:
        #         batch_ids = all_files_id[i : i + 100]
        #     res = self.file.trash(batch_ids)
        #     if res.code == 0:
        #         print(f"✅ 删除成功: {batch_ids}")
        #     else:
        #         print(f"❌ 删除失败: {batch_ids},错误信息: {res.message}")


if __name__ == "__main__":
    pan123 = Pan123openAPI()
    # # 下载单个文件
    fname = "word3prefect6300data.rar"
    pan123.download(fname, onlyurl=False)

    # # # 上传文件
    # pan123.upload(fname, fname, 0, overwrite=True)
    # print("上传完成")
