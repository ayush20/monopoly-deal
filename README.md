# Deal Room

A browser-based, real-time multiplayer property card game for 2–5 players. This repository currently contains the Phase 1 foundation only: application shells, health checks, quality tooling, and documentation. It intentionally contains no game rules or gameplay implementation.

## Architecture

- **Frontend:** React, TypeScript, Vite, and Socket.IO client.
- **Backend:** Flask and Flask-SocketIO, with an authoritative game service planned for a later phase.
- **Deployment target:** static frontend via Cloudflare; one persistent Flask/Socket.IO process on AWS EC2 behind a reverse proxy.
- **State:** in-memory only for the initial single-instance deployment. No database or Redis is included.

The browser receives only a small health/status response today. Future game events will be validated by the backend and projected into player-specific views.

## Prerequisites

- Node.js 20 or newer and npm 10 or newer.
- Python 3.12 or newer.
- [`uv`](https://docs.astral.sh/uv/) for Python dependency management.

## Local setup

1. Copy the example environment file:

   ```sh
   cp .env.example backend/.env
   ```

2. Install backend dependencies:

   ```sh
   cd backend
   uv sync --extra dev
   ```

3. Install frontend dependencies:

   ```sh
   cd frontend
   npm install
   ```

## Development

In one terminal, start the backend:

```sh
cd backend
uv run flask --app app run --debug --port 5000
```

In another terminal, start the frontend:

```sh
cd frontend
npm run dev
```

Open `http://localhost:5173`. The page reports both the HTTP health check and Socket.IO connection status.

## Quality commands

```sh
# backend
cd backend
uv run ruff check .
uv run ruff format --check .
uv run mypy app tests
uv run pytest

# frontend
cd frontend
npm run lint
npm run typecheck
npm run test -- --run
npm run build
```

After the first frontend install, commit the generated `frontend/package-lock.json`; subsequent installs should use `npm ci` locally and in CI.

## Git workflow

- `main` is always intended to be runnable and deployable.
- Create focused branches using `feature/<topic>`, `fix/<topic>`, `docs/<topic>`, or `chore/<topic>`.
- Use imperative Conventional Commit-style messages, for example `feat: add room health endpoint`.
- Open a pull request into `main`, complete the checklist, and require the CI checks to pass before merge.
- Avoid committing secrets, generated dependencies, or environment files. Use `.env.example` for safe placeholders.

See [docs/decisions.md](docs/decisions.md) for product decisions, rule-source policy, and unresolved questions.
