import os
import secrets
import sqlite3
from functools import wraps
from pathlib import Path

from flask import (
    Flask,
    abort,
    flash,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    session,
)

import metrics
from db import (
    delete_server,
    fetch_user,
    init_db,
    insert_server,
    insert_user,
    list_servers,
)
from passwords import hash_password, password_matches

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DATABASE = BASE_DIR / "monitoring.db"
DEFAULT_SECRET_FILE = BASE_DIR / ".secret"
GENERIC_LOGIN_ERROR = "Invalid username or password."
ALLOWED_ROLES = {"admin", "viewer"}


def create_app(config=None):
    app = Flask(__name__)
    app.config.update(
        DATABASE=os.environ.get("MONITOR_DATABASE", str(DEFAULT_DATABASE)),
        SECRET_FILE=os.environ.get("MONITOR_SECRET_FILE", str(DEFAULT_SECRET_FILE)),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=False,
    )
    if os.environ.get("MONITOR_SECRET"):
        app.config["SECRET_KEY"] = os.environ["MONITOR_SECRET"]
    if config:
        app.config.update(config)
    _load_secret(app)
    init_db(app.config["DATABASE"])

    @app.before_request
    def open_db():
        if "db" not in g:
            conn = sqlite3.connect(app.config["DATABASE"])
            conn.row_factory = sqlite3.Row
            g.db = conn

    @app.teardown_appcontext
    def close_db(_error):
        conn = g.pop("db", None)
        if conn is not None:
            conn.close()

    def signed_in():
        return bool(session.get("username"))

    def ensure_csrf():
        token = session.get("csrf_token")
        if not token:
            token = secrets.token_urlsafe(32)
            session["csrf_token"] = token
        return token

    def csrf_ok():
        sent = request.form.get("csrf_token", "")
        expected = session.get("csrf_token", "")
        if not isinstance(sent, str) or not isinstance(expected, str):
            return False
        if not sent or not expected or len(sent) != len(expected):
            return False
        return secrets.compare_digest(sent, expected)

    def login_required(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not signed_in():
                return redirect("/login")
            return view(*args, **kwargs)

        return wrapped

    def admin_required(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not signed_in():
                return redirect("/login")
            if session.get("role") != "admin":
                abort(403)
            return view(*args, **kwargs)

        return wrapped

    @app.get("/login")
    def login_form():
        return render_template("login.html", error=None)

    @app.post("/login")
    def login_submit():
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = fetch_user(g.db, username) if username else None
        if user is None or not password_matches(user["password_hash"], password):
            return render_template("login.html", error=GENERIC_LOGIN_ERROR)
        session.clear()
        session["username"] = user["username"]
        session["role"] = user["role"]
        session["csrf_token"] = secrets.token_urlsafe(32)
        return redirect("/")

    @app.post("/logout")
    def logout():
        session.clear()
        return redirect("/login")

    @app.get("/")
    @login_required
    def index():
        return render_template(
            "index.html",
            servers=list_servers(g.db),
            csrf_token=ensure_csrf(),
            is_admin=session.get("role") == "admin",
            error=None,
        )

    @app.post("/servers")
    @admin_required
    def add_server():
        if not csrf_ok():
            return (
                render_template(
                    "index.html",
                    servers=list_servers(g.db),
                    csrf_token=ensure_csrf(),
                    is_admin=True,
                    error="Invalid request.",
                ),
                400,
            )
        name = request.form.get("name", "").strip()
        address = request.form.get("address", "").strip()
        note = request.form.get("note", "").strip()
        if not name or not address:
            return (
                render_template(
                    "index.html",
                    servers=list_servers(g.db),
                    csrf_token=ensure_csrf(),
                    is_admin=True,
                    error="Name and address are required.",
                ),
                400,
            )
        insert_server(g.db, name, address, note or None)
        return redirect("/")

    @app.post("/servers/<int:server_id>/delete")
    @admin_required
    def remove_server(server_id):
        if not csrf_ok():
            abort(400)
        delete_server(g.db, server_id)
        return redirect("/")

    @app.get("/users")
    @admin_required
    def new_user_form():
        return render_template(
            "users.html",
            csrf_token=ensure_csrf(),
            error=None,
        )

    @app.post("/users")
    @admin_required
    def create_user():
        if not csrf_ok():
            return (
                render_template(
                    "users.html",
                    csrf_token=ensure_csrf(),
                    error="Invalid request.",
                ),
                400,
            )
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        role = (request.form.get("role") or "viewer").strip()
        if not username or not password:
            return (
                render_template(
                    "users.html",
                    csrf_token=ensure_csrf(),
                    error="Username and password are required.",
                ),
                400,
            )
        if role not in ALLOWED_ROLES:
            return (
                render_template(
                    "users.html",
                    csrf_token=ensure_csrf(),
                    error="Unknown role.",
                ),
                400,
            )
        password_hash = hash_password(password)
        try:
            insert_user(g.db, username, password_hash, role)
        except sqlite3.IntegrityError:
            return (
                render_template(
                    "users.html",
                    csrf_token=ensure_csrf(),
                    error="That username is already in use.",
                ),
                400,
            )
        flash("User added.")
        return redirect("/users")

    @app.get("/metrics")
    @login_required
    def metrics_view():
        return jsonify(metrics.collect_all())

    return app


def _load_secret(app):
    if app.config.get("SECRET_KEY"):
        return
    path = Path(app.config["SECRET_FILE"])
    if path.exists() and path.read_text().strip():
        app.config["SECRET_KEY"] = path.read_text().strip()
        return
    key = secrets.token_hex(32)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.write(fd, key.encode("ascii"))
    finally:
        os.close(fd)
    app.config["SECRET_KEY"] = key


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=5000)
