# Demo Monitoring Infrastructure

This demo serves localhost only. Pages are server-rendered. There is no front-end build.

## Run

```bash
./start.sh
```

Then open http://127.0.0.1:5000.

`start.sh` creates a virtual environment if needed, installs dependencies, and starts the app on `127.0.0.1` only.

## Sign in

Sign in at http://127.0.0.1:5000/login.

Seeded account, created on first start:

- Username: `admin`
- Password: `admin123`

Passwords are stored as hashes. The database never stores the plaintext password.

A wrong username or a wrong password both show the same generic error.

The session cookie is `HttpOnly` and `SameSite=Lax`. This demo is plain HTTP on localhost, so the cookie is not `Secure`. On first start the app writes the session secret to `.secret` (gitignored).

Sign out with the Sign out button. It sends `POST /logout` and returns to the sign-in page. A normal page load cannot sign you out.

Every page except sign-in requires a session. Anonymous requests redirect to `/login`.

## Tests

```bash
.venv/bin/pytest
```

## Continuous integration

GitHub Actions workflow: `.github/workflows/ci.yml`.

On every push and pull request the workflow installs the pinned dependencies and runs `pytest`. It has no secrets, SSH keys, or deploy credentials, and it does not publish the app.

The same workflow then smoke-checks boot: it starts the app on `127.0.0.1` with a temporary secret and database, requests `/login`, and stops the process. The seeded demo password stays inside the app process and is not printed.

## Home page

The home page has a header, a server list, and four areas: CPU, memory, network, and ports.

Live numbers are polled from `GET /metrics` every 5 seconds.

CPU shows overall busy percent. Until a second sample exists, the card shows `Collecting…`.

Memory shows four fields: total, available, used, and used percent. Used is total minus available.

Network omits the loopback interface. Each other interface shows its name, received bytes, transmitted bytes, and a per-second rate. Rates are kept in memory only and are not saved.

The ports table lists listening sockets only: protocol, port, and process name when the OS exposes it.

A server whose address is `localhost` is marked `Monitored`. Any other address is marked `Metrics unavailable`. Removing the `localhost` row does not change collection: live numbers are still read from this machine.

The list is preloaded with one row: name `This host`, address `localhost`.

## Servers

An admin can add a server with three fields: name (required), address (required), and note (optional). Addresses are stored as text and are not opened.

An admin can remove a server. The browser asks for confirmation. Viewers do not see add or remove controls, and the server rejects their add and remove requests.

## Users

Admins can add users. Viewers can view metrics only.

To add a viewer, sign in as an admin, open Add user, and submit a username, a password, and the role `viewer` (the default). The password is hashed before it is saved and is not shown again.

There is no control to delete a user.

## Acceptance

The seven checks in [docs/requirements.md](docs/requirements.md#acceptance) are the acceptance list.
