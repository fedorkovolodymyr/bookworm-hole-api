from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings
from app.core.errors import UnauthorizedError


def _fernet() -> Fernet:
    return Fernet(settings.encryption_settings.key.encode())


def encrypt(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    try:
        return _fernet().decrypt(ciphertext.encode()).decode()
    except InvalidToken as exc:
        raise UnauthorizedError("Stored token could not be decrypted") from exc
