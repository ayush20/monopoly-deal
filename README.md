# Deal Room

A browser-based, real-time multiplayer property card game for 2–5 players. The game is playable end to end: lobby with ready/start, turns, banking, properties, improvements, action and rent cards, payments, Just Say No, host controls, pause/reconnect, and a winner screen. The server is authoritative; the socket protocol is documented in [docs/protocol.md](docs/protocol.md).

## Architecture

- **Frontend:** React, TypeScript, Vite, and Socket.IO client.
- **Backend:** Flask and Flask-SocketIO, with an authoritative game service planned for a later phase.
- **Deployment target:** static frontend via Cloudflare; one persistent Flask/Socket.IO process on AWS EC2 behind a reverse proxy.
- **State:** in-memory only for the initial single-instance deployment. No database or Redis is included.

The browser sends commands over Socket.IO and receives a private `room:state` projection after every change, so hidden hands never leave the server. The reconnect token is stored in `localStorage` per room code and `room:reconnect` is sent on load, so refreshing a tab rejoins the room.

## Prerequisites

- Node.js 20 or newer and Yarn 1 (the repo has `yarn.lock`; npm is not used).
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
   yarn install
   ```

## Development

In one terminal, start the backend:

```sh
cd backend
uv run flask --app app run --debug --port 5001
```

In another terminal, start the frontend:

```sh
cd frontend
yarn dev
```

Open `http://localhost:5173`, create a room, and join from a second browser window. Both players press Ready; the host then presses Start game.

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
yarn lint
yarn typecheck
yarn vitest --run
yarn build
```

Install frontend dependencies with `yarn install --frozen-lockfile` in CI. The frontend reads the backend URL from `VITE_API_URL` (default `http://localhost:5001`). TypeScript is pinned to 5.9 because typescript-eslint does not yet support TypeScript 7.

## Git workflow

- `main` is always intended to be runnable and deployable.
- Create focused branches using `feature/<topic>`, `fix/<topic>`, `docs/<topic>`, or `chore/<topic>`.
- Use imperative Conventional Commit-style messages, for example `feat: add room health endpoint`.
- Open a pull request into `main`, complete the checklist, and require the CI checks to pass before merge.
- Avoid committing secrets, generated dependencies, or environment files. Use `.env.example` for safe placeholders.

See [docs/decisions.md](docs/decisions.md) for product decisions, rule-source policy, and unresolved questions.
