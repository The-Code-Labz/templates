# Open Terminal

A lightweight, self-hosted REST API that gives AI agents and automation tools a
dedicated sandboxed shell — command execution, file operations, interactive
terminal sessions, Jupyter notebook execution, and port management, all behind
one API.

Repo: https://github.com/open-webui/open-terminal

## ⚠️ Read this before deploying

**This container's entire purpose is remote command execution.** Treat it like
a root shell exposed over HTTP, because that is exactly what it is.

- `OPEN_TERMINAL_API_KEY` is **mandatory** on anything reachable beyond
  `localhost`. Without it, anyone who can reach the port can run arbitrary
  commands with the container user's permissions. Generate it with
  `openssl rand -hex 32` — never ship the placeholder.
- Do **not** mount `/var/run/docker.sock` unless you fully trust everyone who
  can reach the API. It hands over full control of the host's Docker daemon —
  effectively root on the host (pull/run privileged containers, mount host
  paths, reach host networking).
- Leave `OPEN_TERMINAL_MULTI_USER` off unless every user of this instance is
  trusted at the same level. It only gives each user a separate home
  directory — one kernel, one process list, one network stack are still
  shared. Users can see each other's running commands and exhaust shared
  resources. For real isolation between users, use
  [Terminals](https://github.com/open-webui/terminals) instead (per-user
  containers; requires an Open WebUI Enterprise License in production).
- Lock `OPEN_TERMINAL_CORS_ALLOWED_ORIGINS` down to the real origin(s) that
  will call this from a browser (e.g. your Open WebUI URL). The default `*`
  lets any website attempt cross-origin requests against it.
- If you put this behind Traefik/a reverse proxy on a public domain, consider
  an additional layer in front (forward-auth/SSO, IP allowlist, or VPN-only
  access) on top of the API key — defense in depth matters a lot more here
  than on a typical web app.
- Never publish the host port (`ports:`) when a reverse proxy already reaches
  the container over the Docker network — one less direct path to a shell.

## Image variants

| | `latest` | `slim` | `alpine` | `openshift` |
|---|---|---|---|---|
| Best for | AI agent sandboxes | Production / hardened | Edge / CI / minimal | OpenShift restricted SCC |
| Size | ~4 GB | ~430 MB | ~230 MB | ~430 MB |
| Bundled tooling | Node.js, gcc, ffmpeg, LibreOffice, LaTeX, Docker CLI, data science libs | git, curl, jq | git, curl, jq | git, curl, jq |
| Runtime package installs | ✔ (has `sudo`) | ✘ | ✘ | ✘ |
| Multi-user mode | ✔ | ✘ | ✘ | ✘ |
| Egress firewall | ✔ | ✔ | ✔ | ✘ |

Pick `slim` or `alpine` for anything you're not actively using the full
toolkit for — smaller attack surface, smaller image.

## Setup

1. Copy `.env` next to the `docker-compose.yml` you're using and fill in:
   - `OPEN_TERMINAL_API_KEY` — `openssl rand -hex 32`
   - `OPEN_TERMINAL_CORS_ALLOWED_ORIGINS` — your real frontend origin(s)
2. **`compose/`** — standalone, exposes port `8000` directly on the host.
   Good for local dev / LAN-only use.
3. **`traefik/`** — no host port published, routed in via Traefik labels.
   Edit the `Host()` rule and `certresolver` to match your setup, and make
   sure the `nat` network already exists (`docker network create nat` if
   not) and your Traefik instance is attached to it.

```bash
docker compose up -d
```

Grab the auto-generated key (if you skipped setting one — not recommended)
from the logs:

```bash
docker logs open-terminal
```

## Validating

```bash
curl -s http://localhost:8000/health          # {"status":"ok"} style response
curl -s http://localhost:8000/docs            # interactive API docs (OpenAPI)
```

Through Traefik, swap `localhost:8000` for your configured hostname over
HTTPS.

## Using with Open WebUI

Add it under **Admin/User Settings → Integrations → Open Terminal** (not as a
generic tool server) — this gets you a file-navigation sidebar plus full
terminal access from chat. See the
[upstream docs](https://docs.openwebui.com/features/open-terminal/) for the
Direct Connection vs. System-Level (multi-user, server-proxied) setup.

## Troubleshooting

- **Container shows `unhealthy` but the app logs look fine**: the `slim`/
  `alpine`/`openshift` images ship **no `curl`** — any healthcheck copied
  from a different template (e.g. `CMD curl ...`) will fail every cycle even
  though the app itself is healthy. Use a Python-based check instead, since
  every variant ships Python:
  ```yaml
  healthcheck:
    test: ["CMD", "python3", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=5)"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 30s
  ```
- **401/403 on every request**: missing or wrong `Authorization: Bearer <key>`
  header — check it matches `OPEN_TERMINAL_API_KEY` in `.env`.
- **CORS errors in browser console**: the calling origin isn't in
  `OPEN_TERMINAL_CORS_ALLOWED_ORIGINS`.
- **Multi-user requests returning 400**: multi-user mode requires an
  `X-User-Id` header on every request that touches a user's workspace.

## Persistence

- Single-user: mount `./data:/home/user`
- Multi-user: mount `./data:/home` instead, and set `OPEN_TERMINAL_MULTI_USER=true`

Any volume type works (local bind mount, named volume, NFS, S3-backed FUSE
mount) — Open Terminal just uses whatever filesystem it's mounted on.
