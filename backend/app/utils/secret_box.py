"""
敏感字符串加解密工具
"""
import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.config.settings import settings


def _build_fernet() -> Fernet:
    """
    根据配置种子构建 Fernet 实例

    为什么这样做：
    - Fernet 需要固定长度的 urlsafe base64 key
    - 项目当前只有普通字符串型配置，因此这里统一做一次 SHA-256 派生
    - 这样既能避免明文存储 API Key，又不要求管理员手动生成 Fernet key
    """
    digest = hashlib.sha256(
        settings.get_model_registry_encryption_secret.encode("utf-8")
    ).digest()
    fernet_key = base64.urlsafe_b64encode(digest)
    return Fernet(fernet_key)


def encrypt_secret(secret_value: str) -> str:
    """
    加密敏感字符串

    Args:
        secret_value: 待加密的明文

    Returns:
        加密后的密文

    Raises:
        ValueError: 当输入为空时抛出
    """
    normalized_value = secret_value.strip()
    if not normalized_value:
        raise ValueError("敏感字段不能为空")
    return _build_fernet().encrypt(normalized_value.encode("utf-8")).decode("utf-8")


def decrypt_secret(encrypted_value: str) -> str:
    """
    解密敏感字符串

    Args:
        encrypted_value: 密文

    Returns:
        解密后的明文

    Raises:
        ValueError: 当密文非法或解密失败时抛出
    """
    normalized_value = encrypted_value.strip()
    if not normalized_value:
        raise ValueError("密文不能为空")

    try:
        decrypted_value = _build_fernet().decrypt(
            normalized_value.encode("utf-8")
        )
    except InvalidToken as exc:
        raise ValueError("模型密钥解密失败") from exc

    return decrypted_value.decode("utf-8")

