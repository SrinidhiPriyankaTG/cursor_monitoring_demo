# Implementation TODO

Local demo only. Work top to bottom. Each box is one small change for an AI assistant. Finish that box’s security line and docs line in the same change before starting the next box.

Run the app with `./start.sh`, then open `http://127.0.0.1:5000`. Source of truth: [requirements.md](requirements.md).

## 1. Project initialization and basic UI

- [x] **1.1 Create the project skeleton**
  - Add pinned `requirements.txt` (Flask), `app.py` with a single `/` route, and `start.sh` that creates a virtual environment, installs dependencies, and starts the app on `127.0.0.1:5000`.
  - Security: listen on `127.0.0.1` only. Add `.gitignore` for `.venv/`, `*.db`, and a future local secret file.
  - Docs: add `README.md` with the one run command and a line that this demo serves localhost only.

- [x] **1.2 Add the page shell**
  - Add a base template: header, a server-list area, and four cards labeled CPU, memory, network, and ports. Use placeholder text.
  - Security: ship no third-party scripts or styles. The page has no forms yet, so it accepts no user input.
  - Docs: in the README, name the four areas on the home page.

- [x] **1.3 Make the layout readable**
  - Add one local CSS file: card layout, a simple table style, and visible empty-state text (`No servers yet`, `Collecting…`).
  - Security: keep CSS local. Do not load a CDN.
  - Docs: note in the README that pages are server-rendered and there is no front-end build.

## 2. Add sign-in functionality and unit tests

- [x] **2.1 Add the test harness**
  - Add `pytest` to `requirements.txt` and an app factory so tests can create a client without starting the server.
  - Security: tests use a temporary database and a temporary secret. They never touch a real user database.
  - Docs: add `pytest` to the README as the one test command.

- [x] **2.2 Hash passwords**
  - Add a helper that hashes with Werkzeug and checks with the matching Werkzeug function.
  - Security: the helper never returns or logs the plaintext password.
  - Docs: state in the README that passwords are stored as hashes.
  - Test: round-trip a password, and assert a wrong password fails.

- [x] **2.3 Store users in SQLite**
  - Create the local SQLite file and a `users` table (`username`, `password_hash`, `role`). On first start, insert `admin` with a hash of `admin123` if that user is missing.
  - Security: use parameterized queries. Store the hash only. Username is unique.
  - Docs: document the seeded `admin` / `admin123` sign-in in the README.
  - Test: first init creates one admin; a second init does not duplicate it; the stored value is not `admin123`.

- [x] **2.4 Show the sign-in page**
  - Add `GET /login` with username and password fields. Point the home page placeholder behind a later gate, but leave `/login` public.
  - Security: the password field uses `type="password"`. Render a generic error area with no text on a fresh visit.
  - Docs: add the sign-in URL to the README.
  - Test: `GET /login` returns the form.

- [x] **2.5 Sign in and start a session**
  - `POST /login` checks the hash, then stores the username and role in the Flask session. Wrong username or wrong password both show the same generic error.
  - Security: session cookie is `HttpOnly` and `SameSite=Lax`. Generate the secret into a gitignored local file on first start. This demo is plain HTTP on localhost, so the cookie stays non-`Secure`.
  - Docs: note the cookie flags and the secret file name in the README.
  - Test: correct password sets the session; wrong password returns the generic error and no session.

- [x] **2.6 Sign out**
  - Add `POST /logout` that clears the session and redirects to `/login`.
  - Security: accept logout only as POST so a random page load cannot end the session.
  - Docs: mention sign-out in the README.
  - Test: after logout, the session is empty.

- [x] **2.7 Require sign-in for the home page**
  - Redirect anonymous requests to `/login`. Signed-in users see the placeholder home page.
  - Security: the redirect target is the local login path only.
  - Docs: state that every page except sign-in requires a session.
  - Test: anonymous `GET /` redirects; a signed-in client gets the home page.

## 3. GitHub Actions

- [x] **3.1 Run tests on every push and pull request**
  - Add `.github/workflows/ci.yml`. The job checks out the repo, installs the pinned dependencies, and runs `pytest`.
  - Security: the workflow has no secrets, no SSH keys, and no deploy credentials. It does not publish the app.
  - Docs: add a CI section to the README with the workflow file name.

- [x] **3.2 Smoke-check that the app boots**
  - In the same workflow, start the app on `127.0.0.1` with a temporary secret and database, request `/login`, then stop the process.
  - Security: the smoke job stays on the runner’s localhost. It uses the seeded demo password only inside the test process and does not print it.
  - Docs: describe the smoke check in the README in one or two lines.

## 4. Server list

- [x] **4.1 Store servers**
  - Add a `servers` table (`name`, `address`, `note`). On first start, insert `This host` / `localhost` when the table is empty.
  - Security: parameterized inserts. The address is text to display later. Nothing connects to it.
  - Docs: note the preloaded row in the README.
  - Test: first init inserts one row; second init leaves it as one row.

- [x] **4.2 Show the list on the home page**
  - Replace the empty server area with the stored rows. A row whose address is `localhost` is marked monitored. Any other address is marked `Metrics unavailable`.
  - Security: escape name, address, and note in the template (default Jinja escaping).
  - Docs: describe the two labels in the README.
  - Test: the home page shows `This host` for a signed-in user.

- [x] **4.3 Let an admin add a server**
  - Add a form for name (required), address (required), and note (optional). Include a session CSRF token on the form and check it on POST.
  - Security: reject a missing or wrong CSRF token. Trim fields and reject empty name or address. Do not pass the address to a shell or a socket.
  - Docs: document the three fields in the README.
  - Test: admin can add a row; a bad CSRF token changes nothing.

- [x] **4.4 Let an admin remove a server**
  - Add a remove button with a browser confirm, posting the row id and the CSRF token.
  - Security: delete by numeric id with a parameterized query. Removing a row does not change which machine is read for metrics.
  - Docs: note that the live host is still this machine after the `localhost` row is removed.
  - Test: admin delete removes that id only.

## 5. Roles

- [x] **5.1 Hide admin controls from viewers**
  - Show add and remove only when the session role is `admin`.
  - Security: hiding buttons is not the control. Check the role on the server for every add and remove.
  - Docs: state the admin and viewer split in the README.
  - Test: a viewer `POST` to add or remove returns forbidden and the table is unchanged.

- [x] **5.2 Let an admin add a user**
  - Add a small form: username, password, role (`viewer` or `admin`, default `viewer`). Hash the password before insert.
  - Security: admin-only, with CSRF. Reject a duplicate username. Never render the password or the hash back. Reject an unknown role value.
  - Docs: document how to add a viewer.
  - Test: a new viewer can sign in; a second insert of the same username fails; a viewer cannot open the add-user route.

## 6. Live metrics

Collectors read this host only. Keep the previous CPU and network sample in memory. Write none of these samples to SQLite.

- [x] **6.1 CPU percent**
  - Read `/proc/stat`, compute overall busy percent from the previous sample, and return `Collecting…` until a second sample exists.
  - Security: read the fixed path only. Ignore query parameters.
  - Docs: name the CPU field in the README.
  - Test: feed two fixture samples and assert the percent; the first call reports collecting.

- [x] **6.2 Memory**
  - Read `/proc/meminfo` and return total, available, used (total minus available), and used percent.
  - Security: fixed path only.
  - Docs: name the four memory fields in the README.
  - Test: parse a fixture `meminfo` and assert used equals total minus available.

- [x] **6.3 Network rates**
  - Read `/proc/net/dev`. Skip the loopback interface. Return name, received bytes, transmitted bytes, and a per-second rate from the previous in-memory sample.
  - Security: fixed path only. Rates stay in memory.
  - Docs: note that loopback is omitted and rates are not saved.
  - Test: two fixture samples produce the expected rate; `lo` is absent.

- [x] **6.4 Listening ports**
  - Run `ss` with a fixed argument list for listening TCP and UDP sockets. Show protocol, port, and process name when present.
  - Security: the command is a fixed list. No shell string and no value from the server form is appended.
  - Docs: state that the table is listening sockets only.
  - Test: parse a fixture `ss` listing and assert established rows are dropped.

- [x] **6.5 JSON endpoint and 5-second refresh**
  - Add `GET /metrics` for signed-in users, returning the four sections. A tiny local script on the home page polls it every 5 seconds and fills the cards and the ports table.
  - Security: anonymous requests redirect to login. The script is same-origin and local. A failed section returns a short error string while the other sections still return data.
  - Docs: document the poll interval and `/metrics`.
  - Test: a signed-in client receives JSON; an anonymous client is redirected; one failing reader does not remove the other keys.

- [x] **6.6 Wire the home page to live data**
  - Replace placeholder card text with the polled values. Keep `Collecting…`, `Metrics unavailable`, and reader errors as visible text.
  - Security: insert numbers and names as text, not as HTML.
  - Docs: point the README acceptance list at the seven checks in `requirements.md`.
  - Test: the home page contains the four section labels for a signed-in user.

## 7. Done when

- [x] **7.1 Walk the acceptance list**
  - Run `./start.sh`, sign in as `admin`, confirm the numbers move within 5 seconds, add a viewer, and confirm that viewer cannot add or remove servers.
  - Security: confirm the SQLite file contains a password hash and that server addresses are never opened.
  - Docs: check the boxes in this file and leave the README run steps accurate.
