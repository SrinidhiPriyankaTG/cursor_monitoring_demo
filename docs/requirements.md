# Demo Monitoring Infrastructure — Requirements

Local demo for internal teams who today sign in to Linux servers to check live CPU, memory, network, and port usage. The app runs on the Linux machine where Cursor is running. It shows that host’s live numbers in a read-only web UI.

## Users

| Role | Who | What they can do |
| --- | --- | --- |
| Admin | One seeded account, plus any user an admin creates with the admin role | View metrics. Add and remove server records. Add users. |
| Viewer | L1, L2, and L3 in infrastructure and application teams | View metrics only. |

The demo ships with the admin account only. Viewer accounts are created later in the UI.

## Scope

In scope:

- Sign-in with a hashed password and a server-side session.
- A server list an admin can add to or remove from.
- Live CPU, memory, network, and listening-port numbers for **this Linux host only**.
- A small start script that installs dependencies and runs the app on localhost.

Out of scope:

- SSH, agents, or metrics from any other machine.
- Charts, saved history, alerts, email, or paging.
- Changing metrics, running commands, or opening a shell from the UI.
- Docker, TLS, SSO, and any host other than localhost.

Server records other than this host are inventory only. They appear in the list with metrics marked unavailable. Only the preloaded local host shows live data.

## How to run

From the project directory:

```bash
./start.sh
```

Then open `http://127.0.0.1:5000`.

`start.sh` creates a virtual environment if needed, installs `requirements.txt`, and starts the app bound to `127.0.0.1` only.

Seeded sign-in (created on first start, stored as a hash, never as plaintext):

- Username: `admin`
- Password: `admin123`

## Functional requirements

### 1. Read-only monitoring UI

- After sign-in, the home page lists servers and shows live metrics for this host.
- Metrics refresh every 5 seconds without a manual reload.
- Viewer accounts do not see add, remove, or user-management controls.
- Hiding a control is not enough. The server rejects viewer calls that add or remove servers or users.
- Layout is a simple desktop page: header, server list, metric cards, and a ports table. Empty and “unavailable” states are visible as text, not blank space.

### 2. Sign-in and users

- Unauthenticated requests to any page except sign-in redirect to the sign-in page.
- Passwords are stored only as hashes (Werkzeug password hashing). Comparison uses the matching check function.
- A session cookie keeps the user signed in. The session secret is generated into a local file on first start.
- Sign-out clears the session.
- An admin can add a user with username, password, and role (`viewer` or `admin`). Role defaults to `viewer`.
- Usernames are unique. The password is hashed before it is saved and is never shown again.
- The last remaining admin account cannot be removed. The demo does not need a delete-user screen beyond that rule if no delete control is shipped.
- Failed sign-in shows a generic error. It does not say whether the username exists.

### 3. Server list

- On first start, the app inserts one server: name `This host`, address `localhost`, and this record is the one that is monitored.
- An admin can add a server with a required name, a required address (hostname or IP), and an optional note.
- An admin can remove a server. The action asks for a confirm in the browser.
- The local monitored record can be removed from the list; if it is removed, the metrics view still reads this host and the list simply has no “this host” row until an admin adds one again. Live collection does not follow the address field.
- Viewers can open the list and the local metrics. They cannot add or remove rows.

Addresses typed into the form are stored and displayed. They are not used to open connections.

## Metrics

Collected on the app host by reading local system data (`/proc`, and `ss` for listening sockets). No user input is passed to a shell.

| Area | What is shown |
| --- | --- |
| CPU | Overall busy percent, from the delta of two `/proc/stat` samples. Until the second sample exists, show “Collecting…”. |
| Memory | Total, available, used (total minus available), and used percent, from `/proc/meminfo`. |
| Network | One row per non-loopback interface: name, received bytes, transmitted bytes, and a per-second rate from the previous sample held in memory. Rates are not written to disk. |
| Ports | Listening sockets only: protocol, port, and process name when the OS exposes it. Established connections are omitted. |

If a read fails, that card or table shows a short error and the rest of the page still renders.

## Data stored locally

One SQLite file in the project directory:

- Users: username, password hash, role.
- Servers: name, address, note.

Metric samples are kept in memory only long enough to compute the next CPU and network rate.

## Tech

- Python 3 and Flask.
- Server-rendered pages plus a small script that polls a JSON metrics endpoint every 5 seconds.
- Plain CSS sufficient for a clear, card-based layout. No front-end build step.
- Dependencies pinned in `requirements.txt`.

## Acceptance

1. `./start.sh` serves the UI at `http://127.0.0.1:5000`.
2. `admin` / `admin123` signs in. A wrong password does not.
3. The home page shows live CPU, memory, network, and listening ports for this machine, and the numbers change on their own within 5 seconds.
4. A viewer account can see those numbers and cannot add or remove servers or users, including by calling the form endpoints directly.
5. An admin can add and remove a server record and can add a viewer.
6. The database contains password hashes, not plaintext passwords.
7. The app does not open SSH or any other connection to the addresses stored in the server list.
