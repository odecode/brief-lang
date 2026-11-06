# Design: Full-stack Task Board (Briev-only)

## Overview

A minimal task-board web app built entirely in Briev to exercise and grow the
language. The app itself is deliberately simple; the real deliverable is the
standard-library net stack it forces us to build, tracked in
docs/plans/2026-10-09-fullstack-stdlib-and-net-stack.md.

Three tiers, all Briev, no other languages:

- Frontend: a .rbv page (compiles to TS/WASM) listing tasks and letting the user
  add / toggle / delete them.
- Backend: a .bv native binary - an HTTP/1.1 server exposing a JSON REST API.
- Database: PostgreSQL, reached over its wire protocol by a pure-Briev client in
  the backend (no libpq, no ORM).

## Requirements (kept intentionally light)

A user can: see all tasks; add a task (title); mark a task done/undone; delete a
task. Tasks persist in Postgres across restarts. No auth, no multi-user, no
real-time. Acceptance = the four operations round-trip through all three tiers.

## Data model

One table:

```sql
CREATE TABLE tasks (
  id    SERIAL PRIMARY KEY,
  title TEXT NOT NULL,
  done  BOOLEAN NOT NULL DEFAULT false
);
```

## REST API (backend)

| Method | Path         | Body            | Result |
|--------|--------------|-----------------|--------|
| GET    | /api/tasks   | -               | JSON array of tasks |
| POST   | /api/tasks   | {title}         | created task |
| PUT    | /api/tasks/N | {done}          | updated task |
| DELETE | /api/tasks/N | -               | 204 |

GET / serves the frontend bundle. The backend sets permissive CORS so the .rbv
bundle (opened from file:// or served) can call the API.

## Request flow (add a task)

```
browser (.rbv)  --HTTP POST /api/tasks {title}-->  backend (.bv)
backend  --PG wire: Parse/Bind/Execute INSERT ... RETURNING-->  Postgres
Postgres --DataRow(id,title,done)-->  backend  --HTTP 200 JSON-->  browser
browser re-renders the list from the JSON
```

## Component mapping to stdlib work

- Frontend list/forms: web/dom.bv + web/router.bv (exist); web/fetch.bv EXTEND (S5).
- Backend HTTP server: lib/std/net/http.bv (S4) over lib/std/net/socket.bv (S2).
- JSON encode/decode: lib/std/json.bv (exists; stress-tested here).
- DB access: lib/std/db/pg.bv (S3) over socket (S2) + bytes (S1).

## External dependencies (not Briev, but allowed - they are the environment)

- A running PostgreSQL server on 127.0.0.1:5432 with trust or md5 auth (see the
  stdlib plan Risk 3). This is the database we connect TO, not code we write.
- A browser to open the frontend.

## Non-goals

Auth, sessions, pagination, migrations, connection pooling, TLS, websockets. If any
emerges as easy and useful it can graduate into the stdlib, but none are required.

## Build + run (via the WSL-built brievc, sources on the Windows workspace)

- Backend:  brievc build app/backend/server.bv --out app/backend ; run the binary.
- Frontend: brievc build app/frontend/app.rbv --split ; open the bundle.
- Exact invocation (stdlib path flags, resource root) is pinned once the first
  compile succeeds; recorded in the stdlib plan.
