import pytest

from app.core.encryption import decrypt, encrypt
from app.core.errors import UnauthorizedError


def test_encrypt_produces_different_ciphertext_than_plaintext():
    ciphertext = encrypt("super-secret-token")
    assert ciphertext != "super-secret-token"


def test_decrypt_reverses_encrypt():
    plaintext = "super-secret-token"
    assert decrypt(encrypt(plaintext)) == plaintext


def test_encrypt_is_nondeterministic():
    assert encrypt("same-input") != encrypt("same-input")


def test_decrypt_rejects_invalid_ciphertext():
    with pytest.raises(UnauthorizedError):
        decrypt("not-a-valid-fernet-token")
