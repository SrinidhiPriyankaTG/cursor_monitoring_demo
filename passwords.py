"""Password hashing helpers. Plaintext passwords are never returned or logged."""

from werkzeug.security import check_password_hash, generate_password_hash


def hash_password(password):
    if not isinstance(password, str):
        raise TypeError("password must be a string")
    return generate_password_hash(password)


def password_matches(stored_hash, password):
    if not isinstance(stored_hash, str) or not isinstance(password, str):
        return False
    return check_password_hash(stored_hash, password)
