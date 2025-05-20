import math
import os
import time
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path, PurePosixPath
from typing import Any, BinaryIO, Callable, Iterable, List, Optional, Union

import requests
from py3_wget.main import download_file
from pydantic import BaseModel, TypeAdapter, validate_call
from tenacity import retry, stop_after_attempt, wait_random

from .directlink import DirectLink
from .file import Auth, File
from .offline import Offline
from .oss import Oss
from .share import Share
from .user import User
from .utils.checkdata import UploadInChunks

# 定义允许的单个类型
SingleDirType = Union[str, int, Path, PurePosixPath]

# 定义参数类型,可以是单个值或这些值的序列对象
DirnamesType = Union[SingleDirType, Iterable[SingleDirType]]


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
            upload_name (str | Path | None): 上传云端的文件名. 如果为 None,则使用本地文件名.
            parentFileID (int | str): 上传到云端的目录 ID. 默认为根目录下, 如果使用use_oss,则为云端根目录为空, 如果不使用oss,则为云端目录为0
            overwrite (bool): 是否强制覆盖同名文件. 如果云端存在同名文件,则默认会报错.
            use_oss (bool ): 是否使用 OSS 上传. 默认为 False.
            duplicate (int | None): 当有相同文件名时,文件处理策略(1保留两者,新文件名将自动添加后缀,2覆盖原文件)
            containDir (bool): 上传文件是否包含路径,默认fasle

        Returns:
            文件 ID 或 -1

        """
        filename, upload_name = self._validate_and_prepare_paths(filename, upload_name)

        file_etag = self.file.calculate_md5(filename)
        file_size = Path(filename).stat().st_size
        uploader = self.oss if use_oss else self.file

        # OSS 不能列文件
        if not use_oss:
            if not isinstance(parentFileID, int):
                raise ValueError("parentFileID 必须为 int 类型")
            if not Path(upload_name).is_absolute():
                need_find_name = PurePosixPath("/") / str(upload_name).lstrip("./")
                need_find_name = str(need_find_name)

            file_id, file_item = self.find_file_id_by_path(
                need_find_name, root_id=parentFileID, is_dir=False
            )
            if file_id and overwrite:
                if isinstance(file_id, int):
                    file_id = [file_id]
                if not isinstance(file_id, list):
                    print("❌ fileId 不是list类型,强制删除失败, 退出")
                    return -1
                self.file.trash(file_id)
                warnings.warn(
                    f"云端文件 {need_find_name} 强制移除到回收站", stacklevel=2
                )

        with open(filename, "rb") as f:
            f.seek(0)
            create_kwargs = {
                "parentFileID": parentFileID,
                "filename": str(upload_name),
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
            print("preuploadID:", preuploadID)
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
            print(" 开始上传到云端...")
            print(f" 文件被拆成 {total_sliceNo} 个分片, 分片大小: {sliceSize} 字节")
            print(f" 用 {max_workers} 个线程一起上传哦~")
            if max_workers == 1:
                for i in range(total_sliceNo):
                    if not upload_slice(i):
                        print(f"\n分片 {i} 上传失败,终止上传.")
                        return -1
                    avg = sum(task_upload_per) / total_sliceNo
                    print(f"\r进度: {avg:.1f}%(共{total_sliceNo}分片)", end="")
            else:
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    future_to_slice = {
                        executor.submit(upload_slice, i): i
                        for i in range(total_sliceNo)
                    }
                    for future in as_completed(future_to_slice):
                        slice_id = future_to_slice[future]
                        if not future.result():
                            print(f"\n分片 {slice_id} 上传失败,终止上传.")
                            return -1
                        avg = sum(task_upload_per) / total_sliceNo
                        print(f"\r进度: {avg:.1f}%(共{total_sliceNo}分片)", end="")

            print("\n分片上传完成,开始合并分片...")
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
                    parentFileId=current_id, lastFileId=last_file_id
                )
                if not res.data or not res.data.get("fileList"):
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
            res = self.file.list_v2(parentFileId=parentFileId, lastFileId=lastFileId)

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
    def list_files(self, dirnames: DirnamesType) -> list[dict] | None:
        """
        给定一个绝对目录路径,列出其下所有文件(含子目录)以及查询目录本身的文件信息.

        Args:
            dirnames (DirnamesType): 云盘中的绝对路径目录列表,必须以 '/' 开头或为整数 fileId.

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
        dirnames: DirnamesType,
        output_path: str | Path = ".",
    ) -> None:
        """
        下载指定目录下的所有文件(含子目录).

        Args:
            dirname (DirnamesType): 云盘中的绝对路径目录列表,必须以 '/' 开头或为整数 fileId 的列表.
            output_path (str | Path): 下载保存的目录,默认当前目录.

        Returns:
            None
        """
        all_files = self.list_files(dirnames)
        if all_files is None:
            print("❌ 没有找到该目录")
            return

        # 获取下载链接,下载文件
        Path(output_path).mkdir(parents=True, exist_ok=True)
        print(f" 开始下载到 {output_path}...")
        for file in all_files:
            # 过滤掉查询目录本身
            if str(dirnames) in [str(file["fileId"]), file["filename"]]:
                continue
            self._download_single_file(file, output_path)

    @validate_call
    def upload_dir(
        self,
        dirname: Union[str, Path],
        parentFileID: int = 0,
        upload_dirname: str | None = None,
    ) -> None:
        """
        上传目录到云端.

        Args:
            dirname (Union[str, Path]): 本地目录路径.
            parentFileID (int): 云端目标父目录的 ID,默认为根目录为 0
            upload_dirname (Optional[str]): 云端新建目录的名称. 如果为 None,则使用 parentFileID 指定的目录.

        Returns:
            None
        """
        local_dir = Path(dirname)
        if not local_dir.exists() or not local_dir.is_dir():
            raise ValueError(f"指定的目录不存在或不是目录: {local_dir}")
        # 不能是.开头的文件
        # if Path(dirname).name.startswith("."):
        #     print(f"❌ 目录 {dirname} 不能以 '.' 开头")
        #     return

        # 创建云端目录(如果指定了 upload_dirname)
        target_dir_id = parentFileID
        if upload_dirname:
            res = self.file.mkdir(name=upload_dirname, parentID=parentFileID, skip=True)
            if not res or res.data is None or res.code == 1:
                print(f"❌ 创建目录失败: {upload_dirname}")
                return
            target_dir_id = res.data["dirID"]

        # 遍历本地目录并上传文件
        files = [f for f in local_dir.rglob("*") if f.is_file()]
        print(f"正在上传 {len(files)} 个文件...")
        for file_path in files:
            try:
                print(f"正在上传: {file_path}")
                res = self.upload(
                    str(file_path), str(file_path), target_dir_id, False, 1, True
                )
                if res == -1:
                    print(f"❌ 上传失败: {file_path}")
                else:
                    print(f"✅ 上传成功: {file_path} -> {res}")
            except Exception as e:
                print(f"❌ 上传过程中出现异常: {file_path},错误信息: {e}")

    @validate_call
    def delete_dir(
        self,
        dirnames: DirnamesType,
    ) -> None:
        """
        删除指定目录及其下的所有文件(含子目录).

        Args:
            dirnames (DirnamesType): 云盘中的绝对路径目录列表,必须以 '/' 开头或为整数 fileId.

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
