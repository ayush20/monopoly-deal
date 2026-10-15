# Test report

## Phase 5 backend verification

Run on 2026-10-15 using the local Python environment:

```sh
cd backend
uv run ruff check .
uv run ruff format --check .
uv run mypy app tests
uv run pytest
```

Result: all checks passed; 36 tests passed.

Coverage includes deck composition, deterministic dealing, turn validation, property actions, rent, strict payments, payment obligations, Just Say No response windows, room lifecycle, reconnect pause behavior, private hand projection, and Socket.IO room creation/join rejection.

## Frontend verification

Run on 2026-10-16 with Node 24 and Yarn 1 in `frontend/`:

```sh
yarn lint
yarn typecheck
yarn vitest --run
yarn build
```

Result: lint, type-check and production build passed; 6 Vitest tests passed. Tests cover room entry, `room:reconnect` with the stored token on connect, Start game visible only to the host and enabled only once two players are ready, Ready toggle, hand actions (Bank, Play as property emit the correct `game:*` payloads) and plays being disabled off-turn.

Toolchain fixes made while running checks: pinned `typescript` to `~5.9.3` (typescript-eslint rejects TS 7), added the missing `@testing-library/dom` peer, added `src/vite-env.d.ts`, and raised the TS lib to ES2021.

## Remaining validation before launch

- Exercise a full multi-browser game from lobby through victory after action commands are exposed to Socket.IO.
- Verify reconnect expiry and host controls on separate devices.
- Verify production reverse-proxy WebSocket upgrades and Cloudflare origin configuration.
