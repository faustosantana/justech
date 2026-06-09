from app.core.security import hash_password, verify_password


def test_password_hash_and_verify():
    password = "JaiosAdmin2026!"
    hashed = hash_password(password)
    assert hashed.startswith("$2b$")
    assert verify_password(password, hashed)
    assert not verify_password("wrong-password", hashed)
