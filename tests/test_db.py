import sqlite3

from db import connect, init_db, list_servers
from passwords import password_matches


def test_admin_is_seeded_once(tmp_path):
    path = tmp_path / "users.db"
    init_db(path)
    init_db(path)
    conn = connect(path)
    try:
        rows = conn.execute(
            "SELECT username, password_hash, role FROM users"
        ).fetchall()
    finally:
        conn.close()
    assert len(rows) == 1
    assert rows[0]["username"] == "admin"
    assert rows[0]["role"] == "admin"
    assert rows[0]["password_hash"] != "admin123"
    assert password_matches(rows[0]["password_hash"], "admin123")


def test_localhost_server_is_seeded_once(tmp_path):
    path = tmp_path / "servers.db"
    init_db(path)
    init_db(path)
    conn = connect(path)
    try:
        rows = list_servers(conn)
    finally:
        conn.close()
    assert len(rows) == 1
    assert rows[0]["name"] == "This host"
    assert rows[0]["address"] == "localhost"


def test_queries_are_parameterized(tmp_path):
    path = tmp_path / "inject.db"
    init_db(path)
    conn = connect(path)
    try:
        sneaky = "admin' OR '1'='1"
        row = conn.execute(
            "SELECT username FROM users WHERE username = ?",
            (sneaky,),
        ).fetchone()
        assert row is None
    finally:
        conn.close()
        sqlite3.connect(path).close()
