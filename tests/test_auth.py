from urllib.parse import urlparse

from tests.helpers import login


def test_client_uses_temporary_secret_and_database(app, tmp_path):
    assert app.config["SECRET_KEY"] == "test-secret"
    assert str(tmp_path) in app.config["DATABASE"]
    assert app.config["DATABASE"] != "monitoring.db"


def test_secret_file_is_created_for_a_new_app(tmp_path):
    from app import create_app

    secret = tmp_path / ".secret"
    application = create_app(
        {
            "DATABASE": str(tmp_path / "secret.db"),
            "SECRET_FILE": str(secret),
        }
    )
    assert secret.exists()
    assert secret.read_text() == application.config["SECRET_KEY"]
    assert "admin123" not in secret.read_text()


def test_login_form_is_public(client):
    response = client.get("/login")
    assert response.status_code == 200
    page = response.get_data(as_text=True)
    assert 'type="password"' in page
    assert 'name="username"' in page
    assert "Invalid username or password." not in page


def test_correct_password_sets_session(client):
    response = login(client)
    assert response.status_code == 302
    assert urlparse(response.headers["Location"]).path == "/"
    parts = [part.strip() for part in response.headers["Set-Cookie"].split(";")]
    assert "HttpOnly" in parts
    assert "SameSite=Lax" in parts
    assert "Secure" not in parts
    with client.session_transaction() as sess:
        assert sess["username"] == "admin"
        assert sess["role"] == "admin"


def test_wrong_password_is_generic_and_sets_no_session(client):
    response = login(client, password="not-the-password")
    assert response.status_code == 200
    assert "Invalid username or password." in response.get_data(as_text=True)
    with client.session_transaction() as sess:
        assert "username" not in sess


def test_unknown_user_uses_the_same_error(client):
    response = login(client, username="missing", password="admin123")
    assert response.status_code == 200
    assert "Invalid username or password." in response.get_data(as_text=True)
    with client.session_transaction() as sess:
        assert "username" not in sess


def test_logout_post_clears_the_session(client):
    login(client)
    response = client.post("/logout")
    assert response.status_code == 302
    assert urlparse(response.headers["Location"]).path == "/login"
    with client.session_transaction() as sess:
        assert "username" not in sess
        assert "role" not in sess


def test_logout_get_does_not_clear_the_session(client):
    login(client)
    response = client.get("/logout")
    assert response.status_code == 405
    with client.session_transaction() as sess:
        assert sess["username"] == "admin"


def test_home_requires_sign_in(client):
    anonymous = client.get("/")
    assert anonymous.status_code == 302
    assert urlparse(anonymous.headers["Location"]).path == "/login"
    login(client)
    home = client.get("/")
    assert home.status_code == 200
    page = home.get_data(as_text=True)
    for label in ("CPU", "Memory", "Network", "Ports"):
        assert label in page


def test_cookie_flags_are_explicit(app):
    assert app.config["SESSION_COOKIE_HTTPONLY"] is True
    assert app.config["SESSION_COOKIE_SAMESITE"] == "Lax"
    assert app.config["SESSION_COOKIE_SECURE"] is False


def test_signed_in_home_shows_seeded_server(client):
    login(client)
    page = client.get("/").get_data(as_text=True)
    assert "This host" in page
    assert "Monitored" in page
    assert "Metrics unavailable" not in page
