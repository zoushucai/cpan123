import hashlib
from pathlib import Path
from typing import Optional


def calculate_md5(file_path: Path | str) -> str:
    """计算文件的 MD5 值

    Args:
        file_path (Path | str): 文件路径,可以是 Path 对象或字符串

    Returns:
        str: 文件的 MD5 值

    Raises:
        AssertionError: 文件不存在或路径不是文件或文件大小为0

    """
    if isinstance(file_path, str):
        file_path = Path(file_path)

    assert file_path.exists(), f"❌ 文件不存在: {file_path}"
    assert file_path.is_file(), f"❌ 路径不是文件: {file_path}"
    hash_md5 = hashlib.md5()
    with file_path.open("rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def get_file_md5_blocks(file_path, block_size=32 * 1024 * 1024):
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    block_list = []
    with file_path.open("rb") as f:
        while True:
            chunk = f.read(block_size)
            if not chunk:
                break
            md5 = hashlib.md5(chunk).hexdigest()
            block_list.append(md5)

    return block_list


def encrypt_md5(md5str):
    if len(md5str) != 32:
        return md5str
    for i in range(0, 32):
        v = int(md5str[i], 16)
        if v < 0 or v > 16:
            return md5str
    md5str = md5str[8:16] + md5str[0:8] + md5str[24:32] + md5str[16:24]
    encryptstr = ""
    for e in range(0, len(md5str)):
        encryptstr += hex(int(md5str[e], 16) ^ 15 & e)[2:3]
    return encryptstr[0:9] + chr(ord("g") + int(encryptstr[9], 16)) + encryptstr[10:]


def calculate_slice_md5(file_path):
    """
    计算文件前 256KB 的 MD5 值.

    :param file_path: 文件路径
    :return: 32 位小写的 MD5 字符串
    """
    md5 = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            data = f.read(256 * 1024)  # 读取前 256KB
            md5.update(data)
        return md5.hexdigest()
    except FileNotFoundError:
        print(f"文件未找到: {file_path}")
        return None
    except Exception as e:
        print(f"读取文件时发生错误: {e}")
        return None


def decrypt_md5(encrypted):
    if len(encrypted) != 32:
        return encrypted

    # Step 1: 恢复 encryptstr(含替代位)
    g_digit = ord(encrypted[9]) - ord("g")
    encryptstr = encrypted[:9] + hex(g_digit)[2:] + encrypted[10:]

    # Step 2: 逆异或
    md5_mixed = ""
    for e in range(len(encryptstr)):
        v = int(encryptstr[e], 16)
        orig = v ^ (e & 15)
        md5_mixed += hex(orig)[2:]

    # Step 3: 逆重排
    if len(md5_mixed) != 32:
        return "无法还原:长度不符"

    part1 = md5_mixed[8:16]  # 原 0-7
    part2 = md5_mixed[0:8]  # 原 8-15
    part3 = md5_mixed[24:32]  # 原 16-23
    part4 = md5_mixed[16:24]  # 原 24-31

    recovered_md5 = part1 + part2 + part3 + part4
    return recovered_md5


def calculate_sha256(file_path: str) -> str:
    """
    计算文件的 SHA256 值.
    """
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


def calculate_sha1(file_path: str) -> str:
    """
    计算文件的 SHA1 值.
    """
    sha1_hash = hashlib.sha1()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha1_hash.update(chunk)
    return sha1_hash.hexdigest()


def calculate_sha512(file_path: str) -> str:
    """
    计算文件的 SHA512 值.
    """
    sha512_hash = hashlib.sha512()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha512_hash.update(chunk)
    return sha512_hash.hexdigest()


def check_hash(
    file_path: str,
    expected_md5: Optional[str] = None,
    expected_sha1: Optional[str] = None,
    expected_sha256: Optional[str] = None,
    expected_sha512: Optional[str] = None,
) -> bool:
    """
    校验文件的哈希值.  通过则返回 True, 否则返回 False.

    Args:
        file_path (str): 文件路径.
        expected_md5 (str): 预期的 MD5 值.
        expected_sha1 (str): 预期的 SHA1 值.
        expected_sha256 (str): 预期的 SHA256 值.
        expected_sha512 (str): 预期的 SHA512 值.
    Returns:
        bool: 校验结果, True 表示通过, False 表示失败.
    """
    if not Path(file_path).exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")

    if not Path(file_path).is_file():
        raise ValueError(f"路径不是文件: {file_path}")
    if not expected_md5 and not expected_sha256 and not expected_sha1 and not expected_sha512:
        # 如果没有提供任何校验值, 则直接返回 True
        return True
    if expected_md5:
        actual_md5 = calculate_md5(file_path)
        if actual_md5.lower() == expected_md5.lower():
            return True
    if expected_sha256:
        actual_sha256 = calculate_sha256(file_path)
        if actual_sha256.lower() == expected_sha256.lower():
            return True
    if expected_sha1:
        actual_sha1 = calculate_sha1(file_path)
        if actual_sha1.lower() == expected_sha1.lower():
            return True
    if expected_sha512:
        actual_sha512 = calculate_sha512(file_path)
        if actual_sha512.lower() == expected_sha512.lower():
            return True
    return False
