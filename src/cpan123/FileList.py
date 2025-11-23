import json
import time
from pathlib import Path
from typing import Any, Dict

from pydantic import validate_call
from ratelimit import limits, sleep_and_retry

from .Auth import Auth
from .File import File
from .File2 import File2
from .model.Base import Share123FileModel, UserInfoModel
from .utils.Logger import log


class FileList:
    """封装文件列表相关操作"""

    def __init__(self, auth: Auth, userinfo: UserInfoModel | None = None) -> None:
        self.auth = auth
        self.userinfo = userinfo
        self.file = File(auth, userinfo)
        self.file2 = File2(auth, userinfo)

    @sleep_and_retry
    @limits(calls=1, period=1)
    def _safe_list_v1(self, **kwargs) -> dict:
        """安全调用 list_v1 方法，遵守速率限制"""
        try:
            return self.file.list_v1(**kwargs)
        except Exception as e:
            log.error(f"safe_list_v1 调用失败: {e}")
            raise ValueError("safe_list_v1 调用失败") from e

    @sleep_and_retry
    @limits(calls=1, period=1)
    def _safe_list_v2(self, **kwargs) -> dict:
        """安全调用 list_v2 方法，遵守速率限制"""
        try:
            return self.file.list_v2(**kwargs)
        except Exception as e:
            log.error(f"safe_list_v2 调用失败: {e}")
            raise ValueError("safe_list_v2 调用失败") from e

    @sleep_and_retry
    @limits(calls=5, period=1)
    def _safe_create(self, *args, **kwargs) -> dict:
        """受限速保护的 create 方法，防止超过速率限制"""
        try:
            return self.file2.create(*args, **kwargs)
        except Exception as e:
            log.error(f"safe_create 调用失败: {e}")
            raise ValueError("safe_create 调用失败") from e

    def _timestamp_ms(self, isformat: bool = True) -> str:
        """生成时间戳"""
        try:
            t = time.time()

            if not isformat:
                return str(int(t * 1000))

            local_time = time.localtime(t)
            return f"{time.strftime('%Y%m%d_%H%M%S', local_time)}_{int(t * 1000) % 1000:03d}"
        except Exception as e:
            log.error(f"生成时间戳失败: {e}")
            return str(int(time.time() * 1000))

    def _save_json_safely(self, data: Dict[str, Any], json_path: Path) -> bool:
        """安全保存 JSON 文件"""
        try:
            # 确保目录存在
            json_path.parent.mkdir(parents=True, exist_ok=True)

            # 使用临时文件避免写入过程中断导致文件损坏
            temp_path = json_path.with_suffix(".tmp")

            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)

            # 重命名临时文件为目标文件（原子操作）
            temp_path.rename(json_path)
            return True

        except IOError as e:
            log.error(f"文件IO错误: {e}")
            return False
        except Exception as e:
            log.error(f"保存JSON文件失败: {e}")
            return False

    @validate_call
    def get_file_list_v1(self, parent_id: int, max_tries: int = 20, search_data: str | None = None) -> dict:
        """
        获取指定目录的全部文件（分页，兼容字段，支持搜索）, 并同时返回 fileId 和 fileID, 官方 V1 返回的是 fileID, V2 返回的是 fileId

        Args:
            parent_id: 目录 ID
            max_tries: 最大重试次数
            search_data: 搜索关键字（可选）
        """
        page = 1
        tries = 0
        resjsons = {"code": 0, "message": "ok", "data": {"total": 0, "fileList": []}}

        while tries < max_tries:
            try:
                resjson = self._safe_list_v1(
                    parentFileId=parent_id,
                    page=page,
                    limit=100,
                    orderBy="file_id",
                    orderDirection="asc",
                    trashed=False,
                    searchData=search_data,
                )

                if not resjson or resjson.get("code") != 0 or "data" not in resjson or not isinstance(resjson["data"], dict):
                    tries += 1
                    log.warning(f"v1接口响应异常: {resjson}，重试中... (尝试 {tries}/{max_tries})")
                    time.sleep(2 * (tries + 1))
                    continue

                file_list = resjson.get("data", {}).get("fileList", [])
                total = resjson.get("data", {}).get("total", 0)
                if not isinstance(file_list, list):
                    tries += 1
                    log.warning(f"v1 fileList 不是列表类型: {type(file_list)}，重试中... (尝试 {tries}/{max_tries})")
                    time.sleep(2)
                    continue

                if not file_list and page == 1:
                    log.warning(f"目录 {parent_id} 为空目录")
                    return resjsons

                # 字段兼容处理：fileID -> fileId
                for item in file_list:
                    if "fileID" in item and "fileId" not in item:
                        # V1 返回的是 fileID
                        item["fileId"] = item["fileID"]

                tries = 0
                resjsons["data"]["total"] += len(file_list)
                resjsons["data"]["fileList"].extend(file_list)
                if resjsons["data"]["total"] >= total:
                    log.info(f"目录 {parent_id} 分页获取完成，共 {page} 页，{len(resjsons['data']['fileList'])} 个文件")
                    break

                page += 1

            except Exception as e:
                tries += 1
                log.error(f"v1获取文件列表异常: {e}，重试中... (尝试 {tries}/{max_tries})")
                time.sleep(2 * (tries + 1))
                continue

        if tries >= max_tries:
            log.error(f"目录 {parent_id} 获取失败，已达到最大重试次数")
            return {"code": -1, "message": "获取失败", "data": {"total": 0, "fileList": []}}

        return resjsons

    @validate_call
    def get_file_list_v2(self, parent_id: int, max_tries: int = 20, search_data: str | None = None, search_mode: int | None = None) -> dict:
        """
        获取指定目录的全部文件（分页，兼容字段，支持搜索/模式）, 并同时返回 fileId 和 fileID, 官方 V1 返回的是 fileID, V2 返回的是 fileId

        Args:
            parent_id: 目录 ID
            max_tries: 最大重试次数
            search_data: 搜索关键字（可选）
            search_mode: 搜索模式（可选）


        """
        last_file_id = None
        tries = 0
        resjsons = {"code": 0, "message": "ok", "data": {"total": 0, "fileList": []}}

        while tries < max_tries:
            try:
                resjson = self._safe_list_v2(
                    parentFileId=parent_id,
                    limit=100,
                    searchData=search_data,
                    searchMode=search_mode,
                    lastFileId=last_file_id,
                )

                if not resjson or resjson.get("code") != 0 or "data" not in resjson or not isinstance(resjson["data"], dict):
                    tries += 1
                    log.warning(f"v2接口响应异常: {resjson}，重试中... (尝试 {tries}/{max_tries})")
                    time.sleep(2 * (tries + 1))
                    continue

                data = resjson["data"]
                file_list = data.get("fileList", [])
                if not isinstance(file_list, list):
                    tries += 1
                    log.warning(f"v2 fileList 不是列表类型: {type(file_list)}，重试中... (尝试 {tries}/{max_tries})")
                    time.sleep(2)
                    continue

                if not file_list and last_file_id is None:
                    log.warning(f"目录 {parent_id} (v2) 为空目录")
                    return resjsons

                # 字段兼容处理：fileId -> fileID
                for item in file_list:
                    if "fileId" in item and "fileID" not in item:
                        # V2 返回的是 fileId
                        item["fileID"] = item["fileId"]

                tries = 0
                resjsons["data"]["fileList"].extend(file_list)
                resjsons["data"]["total"] += len(file_list)

                last_file_id = data.get("lastFileId", -1)
                if last_file_id == -1:
                    log.info(f"目录 {parent_id} (v2) 分页获取完成，共 {len(resjsons['data']['fileList'])} 个文件")
                    break

            except Exception as e:
                tries += 1
                log.error(f"v2获取文件列表异常: {e}，重试中... (尝试 {tries}/{max_tries})")
                time.sleep(2 * (tries + 1))
                continue

        if tries >= max_tries:
            log.error(f"目录 {parent_id} (v2) 获取失败，已达到最大重试次数")
            return {"code": -1, "message": "获取失败", "data": {"total": 0, "fileList": []}}

        return resjsons

    @validate_call
    def recursive_list_v1(self, parent_id: int, save_dir: str = "./output", current_path: str = "", verbose: bool = False, depth: int = 0) -> None:
        """
        递归遍历目录并保存每一级目录的文件列表为 JSON，
        并给每一个文件/目录添加 fullpath 字段。

        Args:
            parent_id: 目录 ID
            save_dir: 保存 JSON 文件的目录
            current_path: 当前目录的路径（用于递归）
            verbose: 是否打印详细信息
            depth: 递归深度（内部使用）

        Returns:
            None
        """
        # 防止递归过深
        if depth > 1000:
            log.error(f"递归深度超过限制: {depth}，停止处理目录 {parent_id}")
            return

        try:
            # 确保保存目录存在
            Path(save_dir).mkdir(parents=True, exist_ok=True)

            # 1) 获取当前目录内容
            file_data = self.get_file_list_v1(parent_id)

            # 检查获取结果
            if file_data.get("code") != 0:
                log.error(f"获取目录 {parent_id} 内容失败: {file_data.get('message')}")
                return

            items = file_data["data"]["fileList"]

            # 2) 给每一个 item 添加 fullpath
            for item in items:
                try:
                    filename = item.get("filename", "")
                    if not filename:
                        log.warning(f"目录 {parent_id} 中存在无文件名的项: {item}")
                        continue

                    if current_path:
                        item["fullpath"] = f"{current_path}/{filename}"
                    else:
                        item["fullpath"] = f"/{filename}"
                except Exception as e:
                    log.error(f"处理文件项失败: {item}, 错误: {e}")
                    continue

            # 3) 保存 JSON 文件
            timestamp = self._timestamp_ms()
            # 使用更安全的文件名
            safe_path = current_path.replace("/", "_").replace("\\", "_") or "root"
            if len(safe_path) > 80:
                safe_path = safe_path[:80]  # 限制文件名长度
            json_filename = f"{timestamp}_{parent_id}_{safe_path}.json"
            json_path = Path(save_dir) / json_filename

            if self._save_json_safely(file_data, json_path):
                if verbose:
                    log.info(f"路径: {current_path or '/'} => {json_path.name}, 共 {len(items)} 项")
            else:
                log.error(f"保存目录 {parent_id} 的JSON文件失败")
                # 不立即返回，继续尝试递归子目录

            # 4) 递归进入子目录
            dir_items = [item for item in items if item.get("type") == 1]

            for item in dir_items:
                try:
                    sub_id = item.get("fileID")
                    sub_path = item.get("fullpath")

                    if not sub_id:
                        log.warning(f"子目录项缺少 fileID: {item}")
                        continue

                    self.recursive_list_v1(sub_id, save_dir, current_path=sub_path, verbose=verbose, depth=depth + 1)

                except Exception as e:
                    log.error(f"递归处理子目录失败: {item}, 错误: {e}")
                    continue

        except KeyboardInterrupt:
            log.info("用户中断操作")
            raise
        except Exception as e:
            log.error(f"处理目录 {parent_id} 时发生未预期异常: {e}")
            # 可以选择记录错误但继续处理其他目录

    @validate_call
    def recursive_list_v2(self, parent_id: int, save_dir: str = "./output", current_path: str = "", verbose: bool = False, depth: int = 0) -> None:
        """
        递归遍历目录并保存每一级目录的文件列表为 JSON，
        并给每一个文件/目录添加 fullpath 字段。

        Args:
            parent_id: 目录 ID
            save_dir: 保存 JSON 文件的目录
            current_path: 当前目录的路径（用于递归）
            verbose: 是否打印详细信息
            depth: 递归深度（内部使用）
        Returns:
            None
        """
        # 防止递归过深
        if depth > 1000:
            log.error(f"递归深度超过限制: {depth}，停止处理目录 {parent_id}")
            return

        try:
            # 确保保存目录存在
            Path(save_dir).mkdir(parents=True, exist_ok=True)

            # 1) 获取当前目录内容
            file_data = self.get_file_list_v2(parent_id)

            # 检查获取结果
            if file_data.get("code") != 0:
                log.error(f"获取目录 {parent_id} 内容失败: {file_data.get('message')}")
                return

            items = file_data["data"]["fileList"]

            # 2) 给每一个 item 添加 fullpath
            for item in items:
                try:
                    filename = item.get("filename", "")
                    if not filename:
                        log.warning(f"目录 {parent_id} 中存在无文件名的项: {item}")
                        continue

                    if current_path:
                        item["fullpath"] = f"{current_path}/{filename}"
                    else:
                        item["fullpath"] = f"/{filename}"
                except Exception as e:
                    log.error(f"处理文件项失败: {item}, 错误: {e}")
                    continue

            # 3) 保存 JSON 文件
            timestamp = self._timestamp_ms()
            # 使用更安全的文件名
            safe_path = current_path.replace("/", "_").replace("\\", "_") or "root"
            if len(safe_path) > 80:
                safe_path = safe_path[:80]  # 限制文件名长度
            json_filename = f"{timestamp}_{parent_id}_{safe_path}.json"
            json_path = Path(save_dir) / json_filename

            if self._save_json_safely(file_data, json_path):
                if verbose:
                    log.info(f"路径: {current_path or '/'} => {json_path.name}, 共 {len(items)} 项")
            else:
                log.error(f"保存目录 {parent_id} 的JSON文件失败")
                # 不立即返回，继续尝试递归子目录

            # 4) 递归进入子目录
            dir_items = [item for item in items if item.get("type") == 1]

            for item in dir_items:
                try:
                    sub_id = item.get("fileId")
                    sub_path = item.get("fullpath")

                    if not sub_id:
                        log.warning(f"子目录项缺少 fileId: {item}")
                        continue

                    self.recursive_list_v2(sub_id, save_dir, current_path=sub_path, verbose=verbose, depth=depth + 1)

                except Exception as e:
                    log.error(f"递归处理子目录失败: {item}, 错误: {e}")
                    continue

        except KeyboardInterrupt:
            log.info("用户中断操作")
            raise
        except Exception as e:
            log.error(f"处理目录 {parent_id} 时发生未预期异常: {e}")
            # 可以选择记录错误但继续处理其他目录

    def rapid(
        self,
        data: dict,
        current_path: str = "/",
        duplicate: int = 1,
    ) -> dict:
        """
        优化：支持单文件和批量秒传，返回所有结果列表，增强异常处理和日志输出。

        Args:
            data: 包含文件信息的字典或列表
            current_path: 当前路径（可选）
            duplicate: 文件处理策略(1保留两者,新文件名自动添加后缀,2覆盖原文件)

        Returns:
            dict: 秒传结果统计 {"results": [...], "success_count": int, "failure_count": int}
        """
        assert duplicate in (1, 2), "duplicate 参数必须是 1 或 2"
        results = []
        # 支持单文件和批量
        if all(k in data for k in ("etag", "size", "path")):
            # 单文件
            results = [self._upload_one(data, current_path, duplicate)]
        elif "list" in data and isinstance(data["list"], list):
            results = [self._upload_one(item, current_path, duplicate) for item in data["list"]]
        elif "data" in data and isinstance(data["data"], list):
            results = [self._upload_one(item, current_path, duplicate) for item in data["data"]]
        elif "files" in data and isinstance(data["files"], list):
            # 添加别人的123秒传格式
            results = [self._upload_one(item, current_path, duplicate) for item in data["files"]]
        else:
            raise ValueError("data 格式不正确，需包含 etag/size/path 或 list/data 字段")

        # 返回统计信息
        success_count = sum(1 for r in results if r)
        failure_count = len(results) - success_count
        return {
            "results": results,
            "success_count": success_count,
            "failure_count": failure_count,
        }

    def _upload_one(self, item_data, current_path, duplicate) -> bool:
        """尝试秒传单个文件，返回是否成功秒传"""
        retries = 3
        delay = 1
        for attempt in range(1, retries + 1):
            try:
                item = Share123FileModel(**item_data)
                # 路径拼接，确保以 / 开头
                path = Path(current_path).as_posix()
                if not path.startswith("/"):
                    path = "/" + path
                full_path = (Path(path) / Path(item.path)).as_posix()
                resjson = self._safe_create(
                    parentFileID=0,
                    filename=full_path,
                    size=int(item.size),
                    etag=str(item.etag),
                    duplicate=duplicate,
                    containDir=True,
                )
                code = resjson.get("code")
                if code == 0:
                    reuse = bool(resjson.get("data", {}).get("reuse"))
                    return reuse
                # 授权错误或限流
                if code in (401, 429, 5000, 1) and attempt < retries:
                    time.sleep(delay)
                    continue
                return False
            except Exception as e:
                log.error(f"秒传文件失败: {item_data}, 错误: {e}")
                return False
        return False
