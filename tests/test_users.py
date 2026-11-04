from tests.helpers import csrf_token, login, user_count


def test_admin_can_add_a_viewer_who_can_sign_in(client, app):
    login(client)
    created = client.post(
        "/users",
        data={
            "username": "l2",
            "password": "viewer-pass-9",
            "role": "viewer",
            "csrf_token": csrf_token(client),
        },
        follow_redirects=True,
    )
    page = created.get_data(as_text=True)
    assert created.status_code == 200
    assert "User added." in page
    assert "viewer-pass-9" not in page
    client.post("/logout")
    signed_in = login(client, username="l2", password="viewer-pass-9")
    assert signed_in.status_code == 302
    blocked = client.get("/users")
    assert blocked.status_code == 403


def test_duplicate_username_is_rejected(client, app):
    login(client)
    payload = {
        "username": "l2",
        "password": "viewer-pass-9",
        "role": "viewer",
        "csrf_token": csrf_token(client),
    }
    assert client.post("/users", data=payload).status_code == 302
    again = client.post("/users", data=payload)
    assert again.status_code == 400
    assert "That username is already in use." in again.get_data(as_text=True)
    assert "viewer-pass-9" not in again.get_data(as_text=True)
    assert user_count(app) == 2


def test_unknown_role_is_rejected(client, app):
    login(client)
    before = user_count(app)
    response = client.post(
        "/users",
        data={
            "username": "rootish",
            "password": "viewer-pass-9",
            "role": "superuser",
            "csrf_token": csrf_token(client),
        },
    )
    assert response.status_code == 400
    assert "Unknown role." in response.get_data(as_text=True)
    assert user_count(app) == before


def test_viewer_add_is_forbidden(client, app):
    login(client)
    client.post(
        "/users",
        data={
            "username": "l3",
            "password": "viewer-pass-9",
            "role": "viewer",
            "csrf_token": csrf_token(client),
        },
    )
    client.post("/logout")
    login(client, username="l3", password="viewer-pass-9")
    before = user_count(app)
    response = client.post(
        "/users",
        data={
            "username": "another",
            "password": "viewer-pass-9",
            "role": "admin",
            "csrf_token": csrf_token(client),
        },
    )
    assert response.status_code == 403
    assert user_count(app) == before
