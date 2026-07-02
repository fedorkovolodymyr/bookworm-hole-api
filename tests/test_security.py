from app.services.security import hash_password, verify_password


def test_hash_password_produces_different_hashes_for_same_input():
    assert hash_password("secret") != hash_password("secret")


def test_verify_password_succeeds_for_correct_password():
    assert verify_password("secret", hash_password("secret")) is True


def test_verify_password_fails_for_wrong_password():
    assert verify_password("wrong", hash_password("secret")) is False


def test_verify_password_fails_for_malformed_hash():
    assert verify_password("secret", "not-a-valid-hash") is False


def test_hash_password_uses_argon2id():
    assert hash_password("secret").startswith("$argon2id$")
