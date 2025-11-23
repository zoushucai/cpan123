import base64
import re


def is_valid_md5(md5_str: str) -> bool:
    """检查字符串是否是有效的32位MD5哈希值"""
    return bool(re.match(r"^[a-f0-9]{32}$", md5_str.lower()))


def md5_to_base62(md5_str: str) -> str:
    """将32位MD5字符串转换为base62编码

    Args:
        md5_str: 32位MD5字符串

    Returns:
        base62编码的字符串
    """
    if not is_valid_md5(md5_str):
        raise ValueError("无效的MD5字符串")

    base62_chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"

    # 将16进制字符串转换为整数
    num = int(md5_str, 16)

    # 将整数转换为base62
    if num == 0:
        return base62_chars[0]

    base62_str = ""
    while num > 0:
        num, remainder = divmod(num, 62)
        base62_str = base62_chars[remainder] + base62_str

    return base62_str


def base62_to_md5(base62_str: str) -> str:
    """将base62编码的字符串转换回32位MD5字符串

    Args:
        base62_str: base62编码的字符串

    Returns:
        32位MD5字符串
    """
    if not base62_str:
        raise ValueError("输入字符串不能为空")

    base62_chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"

    # 验证是否是有效的base62
    if not all(char in base62_chars for char in base62_str):
        raise ValueError("无效的base62编码字符串")

    # 将base62字符串转换为整数
    num = 0
    for char in base62_str:
        num = num * 62 + base62_chars.index(char)

    # 将整数转换回16进制字符串
    hex_str = hex(num)[2:]

    # 填充到32位（MD5固定长度）
    hex_str = hex_str.zfill(32)

    # 验证结果
    if not is_valid_md5(hex_str):
        raise ValueError("base62解码后不是有效的MD5哈希值")

    return hex_str


def md5_to_base64(md5_str: str) -> str:
    """将MD5字符串转换为base64编码

    Args:
        md5_str: 32位MD5字符串

    Returns:
        base64编码的字符串
    """
    if not is_valid_md5(md5_str):
        raise ValueError("无效的MD5字符串")

    # 将16进制字符串转换为字节
    md5_bytes = bytes.fromhex(md5_str)

    # 编码为base64
    base64_str = base64.b64encode(md5_bytes).decode()
    return base64_str


def base64_to_md5(base64_str: str) -> str:
    """将base64编码的字符串转换回32位MD5字符串

    Args:
        base64_str: base64编码的字符串

    Returns:
        32位MD5字符串
    """
    if not base64_str:
        raise ValueError("输入字符串不能为空")

    try:
        # 解码base64字符串
        decoded_bytes = base64.b64decode(base64_str)

        # 检查长度
        if len(decoded_bytes) != 16:
            raise ValueError(f"解码后数据长度不是16字节(MD5)，实际得到{len(decoded_bytes)}字节")

        # 将字节转换为16进制字符串
        md5_str = decoded_bytes.hex()

        # 验证结果
        if not is_valid_md5(md5_str):
            raise ValueError("base64解码后不是有效的MD5哈希值")

        return md5_str

    except Exception as e:
        raise ValueError(f"Base64解码失败: {e}") from e


def detect_and_convert_to_md5(encoded_str: str) -> str:
    """自动检测编码类型并转换为MD5

    Args:
        encoded_str: 可能是base62或base64编码的字符串，或原始MD5

    Returns:
        32位MD5字符串
    """
    if not encoded_str:
        raise ValueError("输入字符串不能为空")

    # 如果是原始MD5，直接返回
    if is_valid_md5(encoded_str):
        return encoded_str

    # 尝试base64
    try:
        return base64_to_md5(encoded_str)
    except ValueError:
        pass

    # 尝试base62
    try:
        return base62_to_md5(encoded_str)
    except ValueError:
        pass

    raise ValueError("无法识别编码格式，既不是有效的MD5、base64也不是base62编码")
