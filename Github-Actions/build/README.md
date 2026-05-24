# Build Images

GitHub Actions workflow that validates Docker image builds for both backend and frontend on every push and pull request.

Does **not** push images — this is a build gate only. Image publishing is handled by GitLab CI via Kaniko after the mirror lands.

## What It Does

Runs a parallel matrix build across both services using Docker Buildx with GitHub Actions layer caching.

| Matrix | Dockerfile | Context |
|---|---|---|
| `backend` | `Dockerfile` | `.` |
| `frontend` | `frontend/Dockerfile` | `./frontend` |

## Setup

1. Copy `build.yml` into your repo at `.github/workflows/build.yml`
2. Adjust the matrix if your Dockerfiles are in different locations:

```yaml
matrix:
  include:
    - service: backend
      dockerfile: Dockerfile
      context: .
    - service: frontend
      dockerfile: frontend/Dockerfile
      context: ./frontend
```

Remove the `frontend` matrix entry if your project has no frontend image.

## Notes

- `fail-fast: false` means a failed backend build won't cancel the frontend build and vice versa
- Layer cache is scoped per service (`scope=${{ matrix.service }}`) so they don't collide
- This workflow pairs with `mirror-to-gitlab.yml` — GitHub validates, GitLab builds and pushes
