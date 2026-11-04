import socket
import subprocess

from tests.helpers import csrf_token, login, server_rows


def test_admin_can_add_a_server(client):
    login(client)
    response = client.post(
        "/servers",
        data={
            "name": "  Lab  ",
            "address": " 10.1.1.8 ",
            "note": " rack ",
            "csrf_token": csrf_token(client),
        },
        follow_redirects=True,
    )
    page = response.get_data(as_text=True)
    assert "Lab" in page
    assert "10.1.1.8" in page
    assert "rack" in page
    assert "Metrics unavailable" in page
    assert "This host" in page


def test_server_fields_are_escaped(client):
    login(client)
    response = client.post(
        "/servers",
        data={
            "name": "<b>bold</b>",
            "address": "10.9.9.9",
            "note": "<script>alert(1)</script>",
            "csrf_token": csrf_token(client),
        },
        follow_redirects=True,
    )
    page = response.get_data(as_text=True)
    assert "<b>bold</b>" not in page
    assert "&lt;b&gt;bold&lt;/b&gt;" in page
    assert "<script>alert(1)</script>" not in page


def test_bad_csrf_does_not_add_a_server(client, app):
    login(client)
    before = len(server_rows(app))
    response = client.post(
        "/servers",
        data={"name": "Nope", "address": "10.0.0.2", "csrf_token": "not-the-token"},
    )
    assert response.status_code == 400
    assert len(server_rows(app)) == before
    assert all(row["name"] != "Nope" for row in server_rows(app))


def test_empty_name_or_address_is_rejected(client, app):
    login(client)
    before = len(server_rows(app))
    response = client.post(
        "/servers",
        data={"name": "   ", "address": "   ", "csrf_token": csrf_token(client)},
    )
    assert response.status_code == 400
    assert len(server_rows(app)) == before


def test_admin_delete_removes_only_that_id(client, app):
    login(client)
    client.post(
        "/servers",
        data={
            "name": "Other",
            "address": "10.2.2.2",
            "csrf_token": csrf_token(client),
        },
    )
    rows = server_rows(app)
    other = next(row for row in rows if row["name"] == "Other")
    kept = next(row for row in rows if row["name"] == "This host")
    response = client.post(
        f"/servers/{other['id']}/delete",
        data={"csrf_token": csrf_token(client)},
    )
    assert response.status_code == 302
    remaining = server_rows(app)
    assert [row["id"] for row in remaining] == [kept["id"]]


def test_adding_a_server_does_not_open_its_address(client, monkeypatch):
    def fail_connect(*_args, **_kwargs):
        raise AssertionError("address was opened")

    def fail_run(*_args, **_kwargs):
        raise AssertionError("command was run")

    monkeypatch.setattr(socket, "create_connection", fail_connect)
    monkeypatch.setattr(subprocess, "run", fail_run)
    login(client)
    response = client.post(
        "/servers",
        data={
            "name": "Remote",
            "address": "192.0.2.10",
            "csrf_token": csrf_token(client),
        },
    )
    assert response.status_code == 302


def test_viewer_cannot_add_or_remove(client, app):
    login(client)
    client.post(
        "/users",
        data={
            "username": "l1",
            "password": "viewer-pass-9",
            "role": "viewer",
            "csrf_token": csrf_token(client),
        },
    )
    client.post("/logout")
    login(client, username="l1", password="viewer-pass-9")
    home = client.get("/")
    page = home.get_data(as_text=True)
    assert home.status_code == 200
    assert "This host" in page
    assert "Add server" not in page
    assert "Remove" not in page
    before = [(row["id"], row["name"]) for row in server_rows(app)]
    token = csrf_token(client)
    added = client.post(
        "/servers",
        data={"name": "Blocked", "address": "10.4.4.4", "csrf_token": token},
    )
    removed = client.post(
        "/servers/1/delete",
        data={"csrf_token": token},
    )
    assert added.status_code == 403
    assert removed.status_code == 403
    assert [(row["id"], row["name"]) for row in server_rows(app)] == before
