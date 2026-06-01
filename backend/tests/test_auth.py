from app.services.auth import create_session_token, hash_password, hash_session_token, verify_password


def test_password_hash_round_trip_and_rejects_wrong_password():
    password_hash = hash_password("correct horse battery staple")

    assert verify_password("correct horse battery staple", password_hash)
    assert not verify_password("wrong password", password_hash)


def test_session_token_hash_is_stable_without_storing_raw_token():
    token = create_session_token()
    token_hash = hash_session_token(token)

    assert token not in token_hash
    assert hash_session_token(token) == token_hash
