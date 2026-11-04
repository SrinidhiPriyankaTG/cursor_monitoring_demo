def login(client, username="admin", password="admin123"):
    return client.post(
        "/login",
        data={"username": username, "password": password},
    )


def csrf_token(client):
    with client.session_transaction() as sess:
        return sess["csrf_token"]


def user_count(app):
    import sqlite3

    conn = sqlite3.connect(app.config["DATABASE"])
    try:
        return conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    finally:
        conn.close()


def server_rows(app):
    import sqlite3

    conn = sqlite3.connect(app.config["DATABASE"])
    conn.row_factory = sqlite3.Row
    try:
        return conn.execute(
            "SELECT id, name, address, note FROM servers ORDER BY id"
        ).fetchall()
    finally:
        conn.close()
