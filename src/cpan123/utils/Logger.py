from httpx import Request, Response
from loguru import logger as log


def log_request(request: Request):
    log.info("<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<")
    log.info(f"请求事件钩子: {request.method} {request.url} - 等待响应")
    log.info(f"请求头: {request.headers}")
    log.info(f"请求参数: {request.content}")
    log.info("<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<")


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
