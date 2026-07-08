from pathlib import Path, PurePosixPath

from py3_wget.main import download_file
from pydantic import BaseModel, validate_call
from tqdm import tqdm

from .Auth import Auth
from .File import File
from .File2 import File2
from .model.Base import UserInfoModel
from .utils.Logger import log


class FileItem(BaseModel):
    fileId: int
    filename: str
    full_path: str
    relative_path: str
    etag: str
    model_config = {"extra": "allow"}


class Downloader:
    """文件下载管理类

    功能：
        - 从云端下载单个文件到本地
        - 从云端下载整个文件夹到本地

    """

    def __init__(self, auth: Auth, userinfo: UserInfoModel | None = None) -> None:
        self.auth = auth
        self.userinfo = userinfo
        self.file = File(auth, userinfo)
        self.file2 = File2(auth, userinfo)

    @validate_call
    def download_file(
        self,
        remote_path: str,
        local_path: str | None = None,
        overwrite: bool = False,
        show_progress: bool = True,
    ) -> dict | None:
        """从云端下载单个文件到本地

        Args:
            remote_path: 云端文件路径（绝对路径，如 "/folder/file.txt"）
            local_path: 本地保存路径。如果为 None，保存到当前目录并使用云端文件名
            overwrite: 是否覆盖已存在的本地文件
            show_progress: 是否显示下载进度

        Returns:
            下载信息字典，包含 url、remote_path、local_path、filename、md5

        Example:
            ```python
            # 下载到当前目录
            downloader.download_file("/folder/file.txt")

            # 下载到指定位置
            downloader.download_file("/folder/file.txt", "downloads/myfile.txt")
            ```
        """
        # 转换为 PurePosixPath 处理云端路径
        cloud_path = PurePosixPath(remote_path)

        # 验证路径
        if not cloud_path.is_absolute():
            cloud_path = PurePosixPath("/") / str(cloud_path).lstrip("./")

        if not cloud_path.suffix:
            raise ValueError(f"路径似乎不是文件（没有文件扩展名）: {cloud_path}")

        # 确定本地保存路径
        save_path = Path(cloud_path.name) if local_path is None else Path(local_path)

        # 检查本地文件是否存在
        if save_path.exists() and not overwrite:
            log.warning(f"文件 {save_path} 已存在，跳过下载（使用 overwrite=True 强制覆盖）")
            return None

        # 查找云端文件
        fileId, fileItem = self._find_file_by_path(cloud_path)
        if not fileId or not fileItem:
            log.error(f"云端找不到文件: {cloud_path}")
            return None

        # 获取下载链接
        respjson = self.file.download_info(fileId)
        download_url = respjson.get("data", {}).get("downloadUrl", "")
        if not download_url:
            log.error(f"无法获取下载链接: {cloud_path}")
            return None

        # 构建返回信息
        download_info = {
            "url": download_url,
            "remote_path": str(cloud_path),
            "local_path": str(save_path),
            "filename": fileItem["filename"],
            "md5": fileItem["etag"],
        }

        # 确保父目录存在
        save_path.parent.mkdir(parents=True, exist_ok=True)

        # 下载文件
        try:
            if show_progress:
                log.info(f"下载: {cloud_path} -> {save_path}")

            download_file(
                url=download_url,
                output_path=str(save_path),
                md5=fileItem["etag"],
                overwrite=overwrite,
                max_tries=5,
                retry_seconds=2,
            )

            if show_progress:
                log.info(f"下载完成: {save_path}")

            return download_info
        except Exception as e:
            log.error(f"下载失败: {e}")
            return None

    @validate_call
    def download_folder(
        self,
        remote_path: str,
        local_path: str | None = None,
        overwrite: bool = False,
        show_progress: bool = True,
    ) -> dict:
        """从云端下载整个文件夹到本地

        Args:
            remote_path: 云端文件夹路径（绝对路径，如 "/folder"）
            local_path: 本地保存目录。如果为 None，使用云端文件夹名作为目录名
            overwrite: 是否覆盖已存在的本地文件
            show_progress: 是否显示下载进度

        Returns:
            下载统计信息字典，包含 total、succeeded、failed

        Example:
            ```python
            # 下载到当前目录（会创建文件夹名的目录）
            downloader.download_folder("/my_folder")
            # 结果：./my_folder/...

            # 下载到指定目录
            downloader.download_folder("/my_folder", "downloads")
            # 结果：./downloads/...
            ```
        """
        # 转换为 PurePosixPath 处理云端路径
        cloud_path = PurePosixPath(remote_path)

        # 验证路径
        if not cloud_path.is_absolute():
            cloud_path = PurePosixPath("/") / str(cloud_path).lstrip("./")

        if cloud_path.suffix:
            raise ValueError(f"路径似乎是文件而不是文件夹: {cloud_path}")

        if cloud_path == PurePosixPath("/"):
            raise ValueError("不支持下载根目录，请指定具体文件夹")

        # 确定本地保存目录
        save_dir = Path(cloud_path.name) if local_path is None else Path(local_path)

        save_dir.mkdir(parents=True, exist_ok=True)

        # 查找云端文件夹
        fileId, _ = self._find_file_by_path(cloud_path, is_dir=True)
        if not fileId:
            log.error(f"云端找不到文件夹: {cloud_path}")
            return {"total": 0, "succeeded": 0, "failed": 0, "files": []}

        # 获取文件夹中的所有文件
        file_list = self._get_file_list(fileId, current_path=str(cloud_path), base_path=str(cloud_path))

        # 过滤掉目录，只保留文件
        files_to_download = [f for f in file_list if f["type"] == 0 and f["trashed"] == 0]

        if not files_to_download:
            log.warning(f"文件夹为空: {cloud_path}")
            return {"total": 0, "succeeded": 0, "failed": 0, "files": []}

        # 下载统计
        total = len(files_to_download)
        succeeded = 0
        failed = 0
        results = []

        if show_progress:
            log.info(f"开始下载文件夹: {cloud_path} ({total} 个文件)")

        # 逐个下载文件
        pbar = tqdm(total=total, desc="下载进度", unit="file", disable=not show_progress)

        for file_info in files_to_download:
            try:
                # 构建本地路径（保持目录结构）
                rel_path = file_info["relative_path"]
                local_file_path = save_dir / rel_path

                # 确保父目录存在
                local_file_path.parent.mkdir(parents=True, exist_ok=True)

                # 检查是否需要下载
                if local_file_path.exists() and not overwrite:
                    succeeded += 1
                    results.append({"file": rel_path, "status": "skipped"})
                    pbar.update(1)
                    continue

                # 获取下载链接
                download_url = self.file.download_info(file_info["fileId"]).get("data", {}).get("downloadUrl", "")
                if not download_url:
                    failed += 1
                    results.append(
                        {
                            "file": rel_path,
                            "status": "failed",
                            "error": "无法获取下载链接",
                        }
                    )
                    pbar.update(1)
                    continue

                # 下载文件
                download_file(
                    url=download_url,
                    output_path=str(local_file_path),
                    md5=file_info["etag"],
                    verbose=False,
                    overwrite=overwrite,
                    max_tries=3,
                    retry_seconds=1,
                )

                succeeded += 1
                results.append({"file": rel_path, "status": "success"})
                pbar.update(1)

            except Exception as e:
                failed += 1
                results.append(
                    {
                        "file": file_info.get("relative_path", "unknown"),
                        "status": "failed",
                        "error": str(e),
                    }
                )
                pbar.update(1)

        pbar.close()

        if show_progress:
            log.info(f"下载完成: 总计 {total} 个文件，成功 {succeeded} 个，失败 {failed} 个")

        return {
            "total": total,
            "succeeded": succeeded,
            "failed": failed,
            "files": results,
            "local_path": str(save_dir),
        }

    # ==================== 内部辅助方法 ====================

    def _find_file_by_path(self, cloud_path: PurePosixPath, is_dir: bool = False) -> tuple[int | None, dict | None]:
        """根据云端路径查找文件或文件夹的 ID"""
        if not cloud_path.is_absolute():
            return None, None

        parts = cloud_path.parts[1:]  # 去掉根 "/"
        current_id = 0  # 从根目录开始
        current_item = None

        for index, name in enumerate(parts):
            found = False
            last_file_id = None

            while True:
                resjson = self.file.list_v2(parentFileId=current_id, lastFileId=last_file_id, limit=100)
                file_list = resjson.get("data", {}).get("fileList", [])

                if not file_list:
                    break

                for item in file_list:
                    if item["filename"] == name and item["trashed"] == 0:
                        # 中间路径必须是目录
                        if index < len(parts) - 1 and item["type"] != 1:
                            continue

                        # 最后一部分根据 is_dir 判断
                        if index == len(parts) - 1:
                            expected_type = 1 if is_dir else 0
                            if item["type"] != expected_type:
                                continue

                        current_id = item["fileId"]
                        current_item = item
                        found = True
                        break

                if found:
                    break

                last_file_id = resjson.get("data", {}).get("lastFileId", -1)
                if last_file_id == -1:
                    break

            if not found:
                return None, None

        return current_id, current_item

    def _get_file_list(self, parent_id: int, current_path: str = "", base_path: str = "") -> list[dict]:
        """递归获取文件夹下的所有文件"""
        file_list = []
        last_file_id = None

        while True:
            resjson = self.file.list_v2(parentFileId=parent_id, lastFileId=last_file_id, limit=100)

            if not resjson.get("data") or not resjson["data"].get("fileList"):
                break

            for item in resjson["data"]["fileList"]:
                # 构建完整路径（保持 / 开头）
                item_path = f"{current_path}/{item['filename']}" if current_path else f"/{item['filename']}"

                item["full_path"] = item_path

                # 计算相对路径
                if base_path:
                    try:
                        # 使用 PurePosixPath 计算相对路径
                        relative_path = str(PurePosixPath(item_path).relative_to(base_path))
                    except ValueError:
                        # 如果失败，使用文件名
                        relative_path = item["filename"]
                else:
                    relative_path = item["filename"]

                item["relative_path"] = relative_path

                # 如果是目录，递归获取子文件
                if item["type"] == 1:
                    file_list.extend(self._get_file_list(item["fileId"], item_path, base_path))
                else:
                    file_list.append(item)

            last_file_id = resjson.get("data", {}).get("lastFileId", -1)
            if last_file_id == -1:
                break

        return file_list

    @validate_call
    def download(
        self,
        remote_path: str,
        local_path: str | None = None,
        overwrite: bool = False,
        show_progress: bool = True,
    ) -> dict | None:
        """自动判断远端路径是文件还是文件夹并下载。

        如果 remote_path 指向文件夹，调用 download_folder；如果指向文件，调用 download_file。

        Returns:
            download_file 返回的 dict（单文件）或 download_folder 返回的统计 dict（文件夹）。
        """
        cloud_path = PurePosixPath(remote_path)

        # 规范化云端路径
        if not cloud_path.is_absolute():
            cloud_path = PurePosixPath("/") / str(cloud_path).lstrip("./")

        # 先尝试按文件夹查找
        folder_id, _ = self._find_file_by_path(cloud_path, is_dir=True)
        if folder_id:
            # 如果是文件夹，调用 download_folder
            return self.download_folder(
                remote_path,
                local_path=local_path,
                overwrite=overwrite,
                show_progress=show_progress,
            )

        # 再尝试按文件查找
        file_id, _ = self._find_file_by_path(cloud_path, is_dir=False)
        if file_id:
            return self.download_file(
                remote_path,
                local_path=local_path,
                overwrite=overwrite,
                show_progress=show_progress,
            )

        # 如果两者都找不到，尝试列出父目录看是否存在类似名称（容错）
        # 例如：用户传入的路径可能带/或不带后缀
        print(f"❌ 云端找不到路径: {cloud_path}")
        return None
