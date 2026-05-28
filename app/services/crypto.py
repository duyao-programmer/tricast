# ============================================================================
# AES-256-CBC 加解密服务
# ============================================================================
import json
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from app.config import settings
from loguru import logger
import os


def _pad(data: bytes, block_size: int = 16) -> bytes:
    """PKCS7 填充"""
    padding_len = block_size - (len(data) % block_size)
    return data + bytes([padding_len] * padding_len)


def _unpad(data: bytes, block_size: int = 16) -> bytes:
    """去除 PKCS7 填充"""
    padding_len = data[-1]
    if padding_len < 1 or padding_len > block_size:
        raise ValueError("无效的填充数据")
    return data[:-padding_len]


def encrypt_dict(data: dict) -> str:
    """
    使用 AES-256-CBC 加密字典数据

    Args:
        data: 待加密的字典

    Returns:
        str: Base64 编码的密文（格式: iv_base64:ciphertext_base64）
    """
    import base64

    key = settings.aes_key_bytes
    iv = os.urandom(16)

    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()

    plaintext = json.dumps(data, ensure_ascii=False).encode("utf-8")
    padded = _pad(plaintext)
    ciphertext = encryptor.update(padded) + encryptor.finalize()

    iv_b64 = base64.b64encode(iv).decode("ascii")
    ct_b64 = base64.b64encode(ciphertext).decode("ascii")

    return f"{iv_b64}:{ct_b64}"


def decrypt_to_dict(encrypted: str) -> dict:
    """
    使用 AES-256-CBC 解密为字典

    Args:
        encrypted: 加密字符串（格式: iv_base64:ciphertext_base64）

    Returns:
        dict: 解密后的原始数据
    """
    import base64

    key = settings.aes_key_bytes

    try:
        iv_b64, ct_b64 = encrypted.split(":")
        iv = base64.b64decode(iv_b64)
        ciphertext = base64.b64decode(ct_b64)

        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()

        padded = decryptor.update(ciphertext) + decryptor.finalize()
        plaintext = _unpad(padded)

        return json.loads(plaintext.decode("utf-8"))
    except Exception as e:
        logger.error("AES 解密失败: {}", e)
        raise ValueError(f"解密失败: {e}")
