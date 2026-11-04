from passwords import hash_password, password_matches


def test_hash_round_trip(caplog):
    caplog.set_level("DEBUG")
    stored = hash_password("s3cret-value")
    assert stored != "s3cret-value"
    assert password_matches(stored, "s3cret-value")
    assert not password_matches(stored, "wrong")
    assert "s3cret-value" not in caplog.text
