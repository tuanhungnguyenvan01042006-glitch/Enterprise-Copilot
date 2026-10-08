from app.core.security import hash_password, hash_token, verify_password


def test_argon2id_password_round_trip() -> None:
    password_hash = hash_password("phase1-test-password")

    assert password_hash.startswith("$argon2id$")
    assert verify_password("phase1-test-password", password_hash)
    assert not verify_password("wrong-password", password_hash)


def test_session_token_is_stored_as_a_sha256_hex_digest() -> None:
    token_hash = hash_token("opaque-session-token")

    assert len(token_hash) == 64
    assert token_hash == hash_token("opaque-session-token")