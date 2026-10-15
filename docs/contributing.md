# Contributing workflow

## Branches and commits

Start from an up-to-date `main` branch and create a narrowly scoped branch:

```sh
git switch -c feature/room-lobby
```

Use one concern per commit. Preferred messages follow an imperative Conventional Commit style:

```text
feat: add room creation endpoint
fix: reject expired reconnect token
test: cover rent payment validation
docs: clarify reconnect policy
```

## Pull requests

Open a pull request into `main` using the repository template. Explain user-visible behavior, tests run, and risks. Do not merge with failing required checks. A pull request is not created by this repository setup; it requires a configured remote and GitHub access.

## Definition of done

- Relevant tests, linting, formatting, and type checks pass.
- New behavior has tests.
- Documentation and decision log are updated where behavior or rules change.
- No credentials, production URLs, or private keys are included.
