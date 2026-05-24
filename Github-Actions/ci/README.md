# CI — Syntax & Lint Validation

GitHub Actions workflow that validates both the Python backend and frontend on every push and pull request.

## What It Does

| Job | Checks |
|---|---|
| `validate-backend` | Installs Python deps, syntax-checks every `.py` file |
| `validate-frontend` | Installs Node deps via `npm ci`, runs lint and typecheck |

Both jobs run in parallel.

## Setup

1. Copy `ci.yml` into your repo at `.github/workflows/ci.yml`
2. Adjust the following if needed:

| Variable | Default | Notes |
|---|---|---|
| Python version | `3.12` | Change to match your project |
| Node version | `20` | Change to match your project |
| Frontend path | `frontend/` | Update `working-directory` if different |
| `cache-dependency-path` | `frontend/package-lock.json` | Update if your lockfile is elsewhere |

## Notes

- `npm run lint --if-present` and `npm run typecheck --if-present` skip gracefully if the scripts are not defined in `package.json`
- Remove the `validate-frontend` job entirely if your project has no frontend
- Remove the `validate-backend` job if your project has no Python backend
