import sys
from typing import Literal, Optional

from httpx import Request, Response
from loguru import logger


def log_request(request: Request):
    log.info("<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<")
    log.info(f"请求事件钩子: {request.method} {request.url} - 等待响应")
    log.info(f"请求头: {request.headers}")
    log.info(f"请求参数: {request.content}")
    log.info("<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<")
    pass


def log_response(response: Response):
    log.info("----------------------------------------------------------------------")
    request = response.request
    log.info(f"响应事件钩子: {request.method} {request.url} - 状态码 {response.status_code}")
    log.info(f"响应头: {response.headers}")
    # 先读取响应内容，然后尝试解析为 JSON
    try:
        response.read()
        log.info(f"响应内容: {response.json()}")
    except Exception as e:
        log.error(f"响应内容读取失败: {e}")
    log.info("----------------------------------------------------------------------")
    pass


class SimpleLogger:
    """
    通用日志封装（Loguru 简易封装版）。
    支持全局单例、控制台开关、日志文件。
    """

    _global_instance: Optional["SimpleLogger"] = None
    _configured = False

    def __init__(
        self,
        *,
        verbose: bool = False,
        log_file: Optional[str] = None,
        level: Literal["DEBUG", "INFO", "SUCCESS", "WARNING", "ERROR"] = "INFO",
    ):
        self.verbose = verbose
        self.log_file = log_file
        self.level = level.upper()
        self._configure_logger()

    def _configure_logger(self):
        """配置 loguru sink（只执行一次）"""
        if not SimpleLogger._configured:
            logger.remove()
            SimpleLogger._configured = True

            # 是否打印到控制台
            if self.verbose:
                logger.add(
                    sys.stderr,
                    level=self.level,
                    enqueue=True,
                    colorize=True,
                    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
                )

            # 文件输出
            if self.log_file:
                logger.add(
                    self.log_file,
                    rotation="10 MB",
                    enqueue=True,
                    level=self.level,
                    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
                )

    # ---- 全局单例 ----
    @classmethod
    def global_logger(
        cls,
        *,
        verbose: bool = False,
        log_file: Optional[str] = None,
        level: Literal["DEBUG", "INFO", "SUCCESS", "WARNING", "ERROR"] = "INFO",
    ) -> "SimpleLogger":
        """返回全局单例日志对象，可指定是否打印"""
        if cls._global_instance is None:
            cls._global_instance = cls(verbose=verbose, log_file=log_file, level=level)
        return cls._global_instance

    # ---- 日志方法 ----
    def debug(self, msg: str):
        logger.debug(msg)

    def info(self, msg: str):
        logger.info(msg)

    def success(self, msg: str):
        logger.success(msg)

    def warning(self, msg: str):
        logger.warning(msg)

    def error(self, msg: str):
        logger.error(msg)


log = SimpleLogger.global_logger(verbose=True)
