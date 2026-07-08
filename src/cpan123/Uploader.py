import hashlib
import math
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock

from tqdm import tqdm

from .Auth import Auth
from .File2 import File2
from .model.Base import UserInfoModel
from .utils.md5 import calculate_md5, calculate_sha1


class Uploader:
    """高层次上传器，封装 File2 接口，支持：
    - 单个文件分片上传
    - 单个文件单步上传
    - 目录上传（可多线程，策略可选）

    约定：
    - 单步上传服务域名通过 domain 接口获取
    - 分片上传 slice 使用 create 返回的 servers 任意其一
    """

    def __init__(self, auth: Auth, userinfo: UserInfoModel | None = None) -> None:
        """初始化

        Args:
            auth (Auth): 已授权的 Auth 实例
            userinfo (UserInfoModel | None): 用户信息模型，默认为 None
        """
        self.auth = auth
        self.userinfo = userinfo
        self.file2 = File2(auth, userinfo=userinfo)
        self.chunked_threshold_bytes = 10 * 1024 * 1024

    # ---------------------- 单文件：分片上传 ----------------------
    def upload_file_chunked(
        self,
        file_path: str | Path,
        parentFileID: int = 0,
        duplicate: int = 1,
        containDir: bool = False,
        server: str | None = None,
        slice_size: int | None = None,
        poll_timeout_sec: int = 300,
        remote_path: str | None = None,
        show_progress: bool = True,
        status_callback: Callable[[dict], None] | None = None,
        try_sha1: bool = False,
    ) -> dict:
        """按分片上传单个文件。

        Args:
            file_path: 本地文件路径
            parentFileID: 父目录 id
            duplicate: 重名策略（1 保留两者，2 覆盖原文件）
            containDir: 是否携带路径（为 True 时 filename 传相对路径）
            server: 指定上传域名（可选，不传使用 create 返回 servers[0]）
            slice_size: 指定分片大小（可选，不传使用服务端下发 sliceSize）
            poll_timeout_sec: upload_complete 轮询超时时间
            show_progress: 是否显示上传进度（默认 True）
            status_callback: 上传状态回调，用于上层汇报阶段变化
            try_sha1: 是否尝试 SHA1 秒传（默认 False）

        Returns:
            服务端最终响应 data 字段
        """
        path = Path(file_path)
        assert path.exists() and path.is_file(), f"文件不存在: {path}"

        size = path.stat().st_size
        size_text = self._format_size(size)
        etag = calculate_md5(path)
        # 生成 filename，是否带目录由 containDir 决定
        filename = path.name if not containDir else remote_path or path.name

        # 0) 优先尝试 SHA1 秒传
        if try_sha1:
            sha1 = calculate_sha1(path)
            sha1_resp = self.file2.sha1_reuse(
                parentFileID=parentFileID,
                filename=filename,
                sha1=sha1,
                size=size,
                duplicate=duplicate,
            )
            sha1_data = sha1_resp.get("data", {})
            if sha1_resp.get("code") == 0 and sha1_data.get("reuse") is True and sha1_data.get("fileID", 0) != 0:
                if status_callback:
                    status_callback(
                        {
                            "stage": "done",
                            "file": str(path),
                            "name": path.name,
                            "size": size,
                            "size_text": size_text,
                            "uploaded_parts": 0,
                            "total_parts": 0,
                        }
                    )
                return sha1_data

        # 1) 创建上传任务
        resp = self.file2.create(
            parentFileID=parentFileID,
            filename=filename,
            etag=etag,
            size=size,
            duplicate=duplicate,
            containDir=containDir,
        )

        # 检查响应状态
        if resp.get("code") != 0:
            error_msg = resp.get("message", "未知错误")
            raise RuntimeError(f"创建上传任务失败: {error_msg}")

        data = resp.get("data")
        if not data:
            raise RuntimeError("创建上传任务失败：响应数据为空")

        # 秒传
        if data.get("reuse") is True and data.get("fileID", 0) != 0:
            return data

        preuploadID = data.get("preuploadID")
        if not preuploadID:
            raise RuntimeError("创建分片任务失败：缺少 preuploadID")

        real_slice = int(slice_size or data.get("sliceSize") or 16 * 1024 * 1024)
        upload_server = server or (data.get("servers") or [None])[0]
        if not upload_server:
            raise RuntimeError("创建分片任务失败：缺少可用上传域名 servers")

        # 2) 逐片上传
        total_parts = math.ceil(size / real_slice) if real_slice else 0

        if status_callback:
            status_callback(
                {
                    "stage": "uploading",
                    "file": str(path),
                    "name": path.name,
                    "size": size,
                    "size_text": size_text,
                    "uploaded_parts": 0,
                    "total_parts": total_parts,
                }
            )

        if show_progress:
            with (
                tqdm(
                    total=size,
                    unit="B",
                    unit_scale=True,
                    unit_divisor=1024,
                    desc=f"上传 {filename}",
                ) as pbar,
                path.open("rb") as f,
            ):
                for part_no in range(1, total_parts + 1):
                    chunk = f.read(real_slice)
                    if not chunk:
                        break

                    # 使用 File2.slice 方法上传分片，传入上传服务器地址
                    self.file2.slice(
                        preuploadID=preuploadID,
                        sliceNo=part_no,
                        sliceMD5=Uploader.__md5_bytes(chunk),
                        slice=chunk,
                        upload_server=upload_server,
                    )

                    if status_callback:
                        status_callback(
                            {
                                "stage": "uploading",
                                "file": str(path),
                                "name": path.name,
                                "size": size,
                                "size_text": size_text,
                                "uploaded_parts": part_no,
                                "total_parts": total_parts,
                            }
                        )

                    # 更新进度条
                    pbar.update(len(chunk))
        else:
            with path.open("rb") as f:
                for part_no in range(1, total_parts + 1):
                    chunk = f.read(real_slice)
                    if not chunk:
                        break

                    # 使用 File2.slice 方法上传分片，传入上传服务器地址
                    self.file2.slice(
                        preuploadID=preuploadID,
                        sliceNo=part_no,
                        sliceMD5=Uploader.__md5_bytes(chunk),
                        slice=chunk,
                        upload_server=upload_server,
                    )

                    if status_callback:
                        status_callback(
                            {
                                "stage": "uploading",
                                "file": str(path),
                                "name": path.name,
                                "size": size,
                                "size_text": size_text,
                                "uploaded_parts": part_no,
                                "total_parts": total_parts,
                            }
                        )

        # 3) 完成上传（必要时轮询）
        start = time.time()
        if status_callback:
            status_callback(
                {
                    "stage": "confirming",
                    "file": str(path),
                    "name": path.name,
                    "size": size,
                    "size_text": size_text,
                    "uploaded_parts": total_parts,
                    "total_parts": total_parts,
                }
            )
        while True:
            time.sleep(2)
            done = self.file2.upload_complete(preuploadID=preuploadID)

            # 检查响应状态
            # code=20103 表示文件正在校验中，需要继续轮询
            code = done.get("code", 0)
            if code != 0 and code != 20103:
                error_msg = done.get("message", "未知错误")
                raise RuntimeError(f"完成上传失败: {error_msg}")

            d = done.get("data")
            if d and d.get("completed") and d.get("fileID", 0) != 0:
                if status_callback:
                    status_callback(
                        {
                            "stage": "done",
                            "file": str(path),
                            "name": path.name,
                            "size": size,
                            "size_text": size_text,
                            "uploaded_parts": total_parts,
                            "total_parts": total_parts,
                        }
                    )
                return d

            if time.time() - start > poll_timeout_sec:
                if status_callback:
                    status_callback(
                        {
                            "stage": "timeout",
                            "file": str(path),
                            "name": path.name,
                            "size": size,
                            "size_text": size_text,
                            "uploaded_parts": total_parts,
                            "total_parts": total_parts,
                        }
                    )
                raise TimeoutError("上传完成确认超时")

    # ---------------------- 单文件：单步上传 ----------------------
    def upload_file_single(
        self,
        file_path: str | Path,
        parentFileID: int = 0,
        duplicate: int = 1,
        containDir: bool = False,
        domain: str | None = None,
        single_limit_bytes: int = 1 * 1024 * 1024 * 1024,  # 1GB（接口限制）
        remote_path: str | None = None,
    ) -> dict:
        """单步上传单个文件（小文件）。

        Args:
            file_path: 本地文件路径
            parentFileID: 父目录 id
            duplicate: 重名策略（1 保留两者，2 覆盖原文件）
            containDir: 是否携带路径
            domain: 指定上传域名（不传则自动获取）
            single_limit_bytes: 单步上传大小限制
        """
        path = Path(file_path)
        assert path.exists() and path.is_file(), f"文件不存在: {path}"
        size = path.stat().st_size
        if size > single_limit_bytes:
            raise ValueError("文件过大，请使用分片上传")

        etag = calculate_md5(path)
        filename = path.name if not containDir else remote_path or path.name

        # 选择上传域名
        upload_domain = domain
        if not upload_domain:
            domains = self.file2.domain()

            # 检查响应状态
            if domains.get("code") != 0:
                error_msg = domains.get("message", "未知错误")
                raise RuntimeError(f"获取上传域名失败: {error_msg}")

            arr = domains.get("data", [])
            upload_domain = (arr or [None])[0]
        if not upload_domain:
            raise RuntimeError("获取上传域名失败")

        # 使用 File2.single_create 方法上传，传入上传服务器地址
        with path.open("rb") as fp:
            file_content = fp.read()

        res = self.file2.single_create(
            parentFileID=parentFileID,
            filename=filename,
            etag=etag,
            size=size,
            file=file_content,
            duplicate=duplicate,
            containDir=containDir,
            upload_server=upload_domain,
        )

        # 检查响应状态
        if res.get("code") != 0:
            error_msg = res.get("message", "未知错误")
            raise RuntimeError(f"单步上传失败: {error_msg}")

        data = res.get("data")
        if not data:
            raise RuntimeError("单步上传失败：响应数据为空")

        if data.get("completed") and data.get("fileID", 0) != 0:
            return data
        raise RuntimeError(f"单步上传失败: {res}")

    # ---------------------- 目录上传 ----------------------
    def upload_folder(
        self,
        folder_path: str | Path,
        parentFileID: int = 0,
        method: str = "chunked",  # 'single' | 'chunked' | 'auto'
        max_workers: int = 4,
        single_limit_bytes: int = 1 * 1024 * 1024 * 1024,
        duplicate: int = 1,
        contain_dir: bool = True,
        show_progress: bool = True,
    ) -> dict:
        """上传整个文件夹。

        - method='single'：全部使用单步上传（大于限制的文件会自动切换分片）
        - method='chunked'：全部使用分片上传
        - method='auto'：小于分片阈值走单步，其他分片
        - 当 contain_dir=True 时，远程路径会包含根目录本身，例如：/文件夹名/子目录/文件
        - show_progress: 是否显示上传进度（默认 True）

        返回 (本地文件, data) 列表
        """
        root = Path(folder_path)
        assert root.exists() and root.is_dir(), f"目录不存在: {root}"

        files: list[tuple[Path, str]] = []  # (真实路径, 远程相对路径)
        for p in root.rglob("*"):
            if p.is_file():
                # 统一相对路径（用于 containDir）
                rel = p.relative_to(root)
                remote = f"{root.name}/{rel.as_posix()}" if contain_dir else p.name
                files.append((p, remote))

        results: list[tuple[Path, dict]] = []
        status_map: dict[str, dict] = {}
        status_lock = Lock()

        def _set_status(payload: dict) -> None:
            file_key = str(payload.get("file", ""))
            if not file_key:
                return
            with status_lock:
                status_map[file_key] = payload

        def _clear_status(real_path: Path) -> None:
            with status_lock:
                status_map.pop(str(real_path), None)

        def _progress_text() -> str:
            with status_lock:
                if not status_map:
                    return "空闲"
                snapshots = list(status_map.values())

            priority = {
                "confirming": 0,
                "uploading": 1,
                "failed": 2,
                "timeout": 3,
                "done": 4,
            }
            snapshots.sort(
                key=lambda item: (
                    priority.get(str(item.get("stage")), 99),
                    str(item.get("name", "")),
                )
            )
            current = snapshots[0]
            stage = str(current.get("stage", "uploading"))
            name = str(current.get("name", ""))
            size_text = str(current.get("size_text", ""))
            uploaded_parts = int(current.get("uploaded_parts", 0) or 0)
            total_parts = int(current.get("total_parts", 0) or 0)

            if stage == "confirming":
                stage_text = "等待服务端确认"
            elif stage == "uploading":
                stage_text = f"上传分片 {uploaded_parts}/{total_parts}" if total_parts > 0 else "上传中"
            elif stage == "failed":
                stage_text = "上传失败"
            elif stage == "timeout":
                stage_text = "确认超时"
            else:
                stage_text = "处理中"

            active_count = len(snapshots)
            return f"活跃: {active_count} | {stage_text} | {name} ({size_text})"

        def _result_text(real_path: Path, item: dict) -> str:
            size_text = self._format_size(real_path.stat().st_size)
            if isinstance(item, dict) and "error" in item:
                return f"失败: {real_path.name} ({size_text}) -> {item.get('error')}"

            inner = item.get("data") if isinstance(item, dict) and isinstance(item.get("data"), dict) else item
            if isinstance(inner, dict):
                file_id = int(inner.get("fileID", 0) or 0)
                completed = bool(inner.get("completed"))
                reuse = bool(inner.get("reuse"))
                if file_id != 0 and (completed or reuse):
                    if reuse:
                        return f"已秒传: {real_path.name} ({size_text})"
                    return f"已上传: {real_path.name} ({size_text})"

            return f"失败: {real_path.name} ({size_text}) -> unexpected response"

        def _task(item: tuple[Path, str]) -> tuple[Path, dict]:
            real_path, remote = item
            size = real_path.stat().st_size
            try:
                use_chunked = method == "chunked" or (method == "auto" and size >= self.chunked_threshold_bytes)
                if use_chunked:
                    data = self.upload_file_chunked(
                        real_path,
                        parentFileID=parentFileID,
                        duplicate=duplicate,
                        containDir=contain_dir,
                        remote_path=remote,
                        show_progress=False,  # 多线程环境下禁用单文件进度条
                        status_callback=_set_status,
                    )
                else:
                    _set_status(
                        {
                            "stage": "uploading",
                            "file": str(real_path),
                            "name": real_path.name,
                            "size": size,
                            "size_text": self._format_size(size),
                            "uploaded_parts": 0,
                            "total_parts": 0,
                        }
                    )
                    data = self.upload_file_single(
                        real_path,
                        parentFileID=parentFileID,
                        duplicate=duplicate,
                        containDir=contain_dir,
                        single_limit_bytes=single_limit_bytes,
                        remote_path=remote,
                    )
                    _set_status(
                        {
                            "stage": "done",
                            "file": str(real_path),
                            "name": real_path.name,
                            "size": size,
                            "size_text": self._format_size(size),
                            "uploaded_parts": 0,
                            "total_parts": 0,
                        }
                    )
                return (real_path, data)
            except Exception as e:  # 汇总错误，便于一次性查看
                _set_status(
                    {
                        "stage": "failed",
                        "file": str(real_path),
                        "name": real_path.name,
                        "size": size,
                        "size_text": self._format_size(size),
                        "uploaded_parts": 0,
                        "total_parts": 0,
                    }
                )
                return (real_path, {"error": str(e)})

        # 多线程提交任务
        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            fut_map = {ex.submit(_task, item): item for item in files}

            if show_progress:
                # 显示文件级别的进度条
                with tqdm(total=len(files), desc="上传文件", unit="file") as pbar:
                    pbar.set_postfix_str(_progress_text())
                    for fut in as_completed(fut_map):
                        result = fut.result()
                        results.append(result)
                        tqdm.write(_result_text(result[0], result[1]))
                        _clear_status(result[0])
                        pbar.set_postfix_str(_progress_text())
                        pbar.update(1)
            else:
                for fut in as_completed(fut_map):
                    result = fut.result()
                    results.append(result)
                    _clear_status(result[0])

        # 规范化每个文件的返回，统一为 {code, message, success, data}
        normalized: dict[str, dict] = {}
        for real_path, item in results:
            key = str(real_path)
            # 异常场景
            if isinstance(item, dict) and "error" in item:
                normalized[key] = {
                    "code": 1,
                    "message": str(item.get("error")),
                    "success": False,
                    "data": None,
                }
                continue

            # 解包外层 {code,message,data} 与直接 data 两种形态
            inner = item.get("data") if isinstance(item, dict) and isinstance(item.get("data"), dict) else item
            if not isinstance(inner, dict):
                normalized[key] = {
                    "code": 1,
                    "message": "unexpected response",
                    "success": False,
                    "data": None,
                }
                continue

            file_id = int(inner.get("fileID", 0) or 0)
            completed = bool(inner.get("completed"))
            reuse = bool(inner.get("reuse"))
            success = file_id != 0 and (completed or reuse)

            normalized[key] = {
                "code": 0 if success else 1,
                "message": "ok" if success else "failed",
                "success": success,
                "data": inner,
            }

        # 统计
        total = len(normalized)
        succeeded = sum(1 for v in normalized.values() if v.get("success"))
        failed = total - succeeded

        return {
            "code": 0 if failed == 0 else 1,
            "message": "ok" if failed == 0 else "partial failure",
            "total": total,
            "succeeded": succeeded,
            "failed": failed,
            "data": normalized,
            "x-traceID": "my-trace-id",
        }

    @staticmethod
    def __md5_bytes(b: bytes) -> str:
        h = hashlib.md5()
        h.update(b)
        return h.hexdigest()

    @staticmethod
    def _format_size(size: int) -> str:
        """将字节数转换为人类可读格式"""
        size_float = float(size)
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size_float < 1024.0:
                return f"{size_float:.1f}{unit}"
            size_float /= 1024.0
        return f"{size_float:.1f}PB"

    # 如果选择的是文件,则调用 upload_file_chunked
    # 如果是目录,则调用 upload_folder
    def upload(
        self,
        file_path: str | Path,
        parentFileID: int = 0,
        duplicate: int = 1,
        contain_dir: bool = True,
        show_progress: bool = True,
        method: str = "chunked",
    ) -> dict:
        """根据路径类型选择上传方式。

        Args:
            file_path: 本地文件或目录路径
            parentFileID: 父目录 id
            duplicate: 当有相同文件名时，文件处理策略（1保留两者，新文件名将自动添加后缀，2覆盖原文件）
            show_progress: 是否显示上传进度（默认 True）
            method: 上传方式，默认统一走分片上传

        Returns:
            统一汇总后的上传结果

        """
        path = Path(file_path)

        if path.is_file():
            try:
                if method == "chunked":
                    data = self.upload_file_chunked(
                        file_path=path,
                        parentFileID=parentFileID,
                        duplicate=duplicate,
                        containDir=contain_dir,
                        show_progress=show_progress,
                    )
                elif method == "single":
                    data = self.upload_file_single(
                        file_path=path,
                        parentFileID=parentFileID,
                        duplicate=duplicate,
                        containDir=contain_dir,
                    )
                else:
                    size = path.stat().st_size
                    if size >= self.chunked_threshold_bytes:
                        data = self.upload_file_chunked(
                            file_path=path,
                            parentFileID=parentFileID,
                            duplicate=duplicate,
                            containDir=contain_dir,
                            show_progress=show_progress,
                        )
                    else:
                        data = self.upload_file_single(
                            file_path=path,
                            parentFileID=parentFileID,
                            duplicate=duplicate,
                            containDir=contain_dir,
                        )
            except Exception as e:
                return {
                    "code": 1,
                    "message": "failed",
                    "total": 1,
                    "succeeded": 0,
                    "failed": 1,
                    "data": {
                        str(path): {
                            "code": 1,
                            "message": str(e),
                            "success": False,
                            "data": None,
                        }
                    },
                    "x-traceID": "my-trace-id",
                }

            success = False
            if isinstance(data, dict):
                file_id = int(data.get("fileID", 0) or 0)
                completed = bool(data.get("completed"))
                reuse = bool(data.get("reuse"))
                success = file_id != 0 and (completed or reuse)

            resp = {
                "code": 0 if success else 1,
                "message": "ok" if success else "failed",
                "total": 1,
                "succeeded": 1 if success else 0,
                "failed": 0 if success else 1,
                "data": {},
                "x-traceID": "my-trace-id",
            }
            if not success:
                resp["data"] = {
                    str(path): {
                        "code": 1,
                        "message": "failed",
                        "success": False,
                        "data": data if isinstance(data, dict) else None,
                    }
                }
        elif path.is_dir():
            resp = self.upload_folder(
                folder_path=path,
                parentFileID=parentFileID,
                method=method,
                duplicate=1 if duplicate == 1 else 2,
                contain_dir=contain_dir,
                show_progress=show_progress,
            )
        else:
            raise ValueError(f"路径既不是文件也不是目录: {path}")
        # 单文件成功时不返回明细，避免输出过大
        if path.is_file() and resp.get("succeeded") == resp.get("total"):
            resp["data"] = {}
        return resp
