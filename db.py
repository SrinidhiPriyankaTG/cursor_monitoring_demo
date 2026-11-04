"""Local SQLite storage for users and server inventory."""

import sqlite3

from passwords import hash_password

SEEDED_USERNAME = "admin"
SEEDED_PASSWORD = "admin123"
SEEDED_ROLE = "admin"
SEEDED_SERVER_NAME = "This host"
SEEDED_SERVER_ADDRESS = "localhost"


def connect(path):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(path):
    conn = connect(path)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS servers (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                address TEXT NOT NULL,
                note TEXT
            )
            """
        )
        existing = conn.execute(
            "SELECT id FROM users WHERE username = ?",
            (SEEDED_USERNAME,),
        ).fetchone()
        if existing is None:
            conn.execute(
                "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                (SEEDED_USERNAME, hash_password(SEEDED_PASSWORD), SEEDED_ROLE),
            )
        count = conn.execute("SELECT COUNT(*) AS n FROM servers").fetchone()["n"]
        if count == 0:
            conn.execute(
                "INSERT INTO servers (name, address, note) VALUES (?, ?, ?)",
                (SEEDED_SERVER_NAME, SEEDED_SERVER_ADDRESS, None),
            )
        conn.commit()
    finally:
        conn.close()


def fetch_user(conn, username):
    return conn.execute(
        "SELECT username, password_hash, role FROM users WHERE username = ?",
        (username,),
    ).fetchone()


def insert_user(conn, username, password_hash, role):
    conn.execute(
        "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
        (username, password_hash, role),
    )
    conn.commit()


def list_servers(conn):
    return conn.execute(
        "SELECT id, name, address, note FROM servers ORDER BY id"
    ).fetchall()


def insert_server(conn, name, address, note):
    conn.execute(
        "INSERT INTO servers (name, address, note) VALUES (?, ?, ?)",
        (name, address, note),
    )
    conn.commit()


def delete_server(conn, server_id):
    cursor = conn.execute("DELETE FROM servers WHERE id = ?", (server_id,))
    conn.commit()
    return cursor.rowcount
